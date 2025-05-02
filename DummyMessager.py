import contextlib
import os

from typing import List

from fastapi import FastAPI
from sqlalchemy import DateTime, UniqueConstraint, Column, Integer, String, Text, select, and_, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.functions import now
from pydantic import BaseModel
from dotenv import load_dotenv


Base = declarative_base()
load_dotenv()

MAX_MESSAGES = 10


class Message(Base):
    __tablename__ = 'messages'
    __table_args__ = (
        UniqueConstraint('name', 'user_message_count', name='uq_name_message_count'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String)
    text = Column(Text)
    created_at = Column(DateTime, default=now())
    user_message_count = Column(Integer, nullable=True)


class MessageItem(BaseModel):
    name: str
    text: str


class MessageResponse(BaseModel):
    id: int
    name: str
    text: str
    created_at: str
    user_message_count: int


class ItemsResponse(BaseModel):
    items: List[MessageResponse]


def get_db_url():
    """Получаем из виртуальных переменных данные для подключение к БД"""
    user_db = os.getenv("DB_USER")
    password_db = os.getenv("DB_PASSWORD")
    host_db = os.getenv("DB_HOST")
    port_db = os.getenv("DB_PORT")
    name_db = os.getenv("DB_NAME")

    return f"postgresql+asyncpg://{user_db}:{password_db}@{host_db}:{port_db}/{name_db}"


async def prep_db():
    db_url = get_db_url()
    engine = create_async_engine(db_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл FastAPI приложение"""
    # При старте приложения
    await prep_db()
    yield


app = FastAPI(lifespan=lifespan)
db_url = get_db_url()

engine = create_async_engine(
    db_url,
    echo=True,
    pool_size=30,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    connect_args={
        "command_timeout": 60,
        "timeout": 10,
    }
)

@app.post('/new_message/')
async def create_and_get_last_messages(message_json: MessageItem) -> ItemsResponse:
    """Единственный url для создания одного сообщения
    и возврата последних десяти созданных сообщений"""
    async_session = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )
    message = message_json.model_dump()
    async with async_session() as session:
        while True:
            try:
                async with session.begin():
                    last_count = (await session.execute(
                        select(Message.user_message_count)
                        .where(Message.name == message.get("name"))
                        .order_by(Message.id.desc())
                        .limit(1)
                    )).scalar_one_or_none()

                    if last_count is not None:
                        next_count = last_count + 1
                    else:
                        next_count = 1

                    new_message = Message(
                        name=message.get("name"),
                        text=message.get("text"),
                        user_message_count=next_count
                    )

                    session.add(new_message)
                    await session.flush()
                    result = await session.execute(
                        select(Message)
                        .order_by(Message.id.desc())
                        .limit(MAX_MESSAGES)
                    )
                    messages = result.scalars().all()
                    break
            except IntegrityError:
                print("Ошибка, транзакция откатилась")

    items = [MessageResponse(
        id=msg.id, name=msg.name,
        text=msg.text,
        user_message_count=msg.user_message_count,
        created_at=msg.created_at.isoformat()
    ) for msg in messages]
    return ItemsResponse(items=items)





