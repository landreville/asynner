import asyncio
import sys
import logging
import time
import json
from concurrent import futures
from datetime import datetime
from cornice import Service
from asynner.rbow import asgi_view
from asynner import sasync

log = logging.getLogger(__name__)


def get(path):
    name = path[1:]
    svc = Service(name=name, path=path)
    setattr(sys.modules[__name__], f'{name}_svc', svc)
    return svc.get()


@get('/sequential')
def sequential(request):
    """Run all "external" requests in sequence."""
    start = datetime.now()

    results = []
    for i in range(5):
        results.append(external_fn(f'sequential-{id(request)}-{i}'))

    end = datetime.now()
    log.info(f'Finished request: {(end - start).total_seconds()}')
    return {'data': results}


@get('/async-scoped')
def async_scoped(request):
    """Run all "external" requests asynchronously in a new event loop."""

    start = datetime.now()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = [
        asyncio.ensure_future(
            external_async_fn(f'async-scoped-{id(request)}-{i}')
        )
        for i in range(5)
    ]
    future = asyncio.gather(*tasks)
    results = loop.run_until_complete(future)

    end = datetime.now()
    log.info(f'Finished request: {(end - start).total_seconds()}')
    return {'data': results}


@get('/async-worker')
def async_worker(request):
    """
    Run all "external" requests asynchronously in an existing event loop that
    lives in a dedicated thread.
    """
    start = datetime.now()

    running = [
        asyncio.run_coroutine_threadsafe(
            external_async_fn(f'async-worker-{id(request)}-{i}'),
            loop=request.loop
        )
        for i in range(5)
    ]
    done, not_done = futures.wait(running, timeout=3)
    results = [ftr.result() for ftr in done]

    end = datetime.now()
    log.info(f'Finished request: {(end - start).total_seconds()}')
    return {'data': results}


@get('/async-per-worker')
def async_per_worker(request):
    """
    Run all "external" requests asynchronously in an existing event loop
    that is created in each thread processing requests.
    """
    start = datetime.now()
    
    asyncio.get_event_loop()

    running = [
        external_async_fn(f'async-worker-{id(request)}-{i}')
        for i in range(5)
    ]
    
    done, not_done = sasync.wait(running, timeout=3)
    results = [ftr.result() for ftr in done]

    end = datetime.now()
    log.info(f'Finished request: {(end - start).total_seconds()}')
    return {'data': results}


@asgi_view('/async-view')
async def asgi_async_view(conn):
    start = datetime.now()

    running = [
        external_async_fn(f'async-view-{i}') for i in range(5)
    ]
    results = await asyncio.gather(*running)

    end = datetime.now()

    await conn.send(json.dumps({'data': results}))


@asgi_view('/ws', protocol='websocket')
async def asgi_ws_view(conn):
    while True:
        message = await conn.receive()
        if message['type'] == 'websocket.connect':
            await conn.send({'type': 'websocket.accept'})
        if message['type'] == 'websocket.receive':
            message_text = message.get('text')
            log.info(f'Received: {message_text}')
            await conn.send({'type': 'websocket.send', 'text': f'Pong: {message_text}'})


def external_fn(value, wait_time=1.0):
    time.sleep(wait_time)

    return {'wait_time': wait_time,
            'finished': time.monotonic(),
            'value': value}


async def external_async_fn(value, wait_time=1.0):
    await asyncio.sleep(wait_time)

    return {'wait_time': wait_time,
            'finished': time.monotonic(),
            'value': value}
