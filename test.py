import asyncio
import aiohttp
import argparse
from datetime import datetime


def main(url, path, iterations=5, print_responses=False):
    url = f'{url}/{path}'
    loop = asyncio.get_event_loop()
    loop.run_until_complete(make_requests(url, iterations, print_responses))


async def make_requests(url, iterations, print_responses):
    batch_start = datetime.now()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(iterations):
            tasks.append(
                asyncio.ensure_future(make_request(session, url, print_responses))
            )
        await asyncio.gather(*tasks)

    batch_end = datetime.now()
    print(f'Finished requests: {(batch_end - batch_start).total_seconds()}')


async def make_request(session, url, print_responses):
    async with session.get(url) as resp:
        results = await resp.json()
        if print_responses:
            print('\n'.join([r['value'] for r in results['data']]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Run concurrent requests to the app.')
    parser.add_argument('-u', '--url', default='http://localhost:6544')
    parser.add_argument('-i', '--iterations', default=5, type=int)
    parser.add_argument('-p', '--path', default='sequential')
    parser.add_argument('--print', default=False, action='store_true')
    args = parser.parse_args()
    main(args.url, args.path, args.iterations, args.print)
