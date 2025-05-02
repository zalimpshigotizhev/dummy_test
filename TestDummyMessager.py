import asyncio
import json

from datetime import datetime
import random
from pprint import pprint

import aiohttp

messages_dict = []

async def worker(num: int, who: str, host_url: str, message: str):
    """Один экземпляр запроса происходит в этой функции"""
    data = {
        "name": who,
        "text": message
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
                host_url,
                json=data,
        ) as response:
            if response.status == 500:
                print(f"\033[31mStatus №{num} : {response.status}\033[0m")
            else:
                print(f"\033[32mStatus №{num} : {response.status}\033[0m")
                # pprint(await response.json())



async def main():
    """Entrypoint"""
    hosts = ["http://localhost:8000/new_message/", "http://localhost:8001/new_message/"]
    names = [
        "Алексей",
        "Мария",
        "Иван",
        "Екатерина",
        "Дмитрий",
        "Анна",
        "Сергей",
        "Ольга",
        "Артем",
        "София"
    ]
    message = "**message**"


    start_time = datetime.now()
    counter = 0

    for _ in range(100):
        works = []
        for _ in range(50):
            counter += 1
            works.append(
                worker(
                    num=counter,
                    who=random.choice(names),
                    host_url=random.choice(hosts),
                    message=message
                )
            )
        await asyncio.gather(*works)

    print("-------> Результаты выполнения <-------")
    total_time = (datetime.now() - start_time).seconds
    print("Операция 5000 запросов длилась: ", total_time)
    print("Время работы одного запроса: ", total_time / 5000)
    print("Пропускная способность (Запросов в секунду): ", 5000 / total_time)



if __name__ == '__main__':
    asyncio.run(main())
