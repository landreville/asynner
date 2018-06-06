import asyncio
import aiohttp
import argparse
from datetime import datetime


def main(path='sequential', iterations=5):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(make_requests(path, iterations))


async def make_requests(path, iterations):
    batch_start = datetime.now()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(iterations):
            tasks.append(
                asyncio.ensure_future(make_request(session, path))
            )
        await asyncio.gather(*tasks)

    batch_end = datetime.now()
    print(f'Finished requests: {(batch_end - batch_start).total_seconds()}')


async def make_request(session, path):
    async with session.get(f'http://localhost:6544/{path}') as resp:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--iterations', default=5, type=int)
    parser.add_argument('-p', '--path', default='sequential')
    args = parser.parse_args()
    main(args.path, args.iterations)
