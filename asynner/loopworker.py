import asyncio
import threading


def includeme(config):
    loop = asyncio.new_event_loop()
    LoopThread(loop).start()

    config.add_request_method(
        lambda request: loop,
        'loop',
        property=True,
        reify=True
    )

    config.add_request_method(
        run_coroutine,
        'await',
    )


def run_coroutine(request, coroutine):
    loop = request.loop

    cfuture = asyncio.run_coroutine_threadsafe(
        coroutine,
        loop
    )

    afuture = asyncio.wrap_future(cfuture, loop=loop)

    return afuture


class LoopThread(threading.Thread):

    def __init__(self, loop):
        threading.Thread.__init__(self, name='LoopThread')
        self._loop = loop

    def run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

