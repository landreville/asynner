"""
Run an asyncio loop in it's own thread for scheduling awaitables from
within Pyramid views.

Adds a request property `loop` that returns the loop running
in it's own thread. Use this loop with `asyncio.run_coroutine_threadsafe`
to run awaitables. For example::
    
    import asyncio
    from concurrent import futures
    
    def my_view(request):
        future = asyncio.run_coroutine_threadsafe(my_coroutine(), request.loop)
        done, not_done = futures.wait(running, timeout=3)
        results = [ftr.result() for ftr in done]
        return {'done': results}

A request method is added that allows running a single awaitable and
blocking until it's results are complete or timeout passes.
Example usage::
    
    from loopworker import AwaitableTimeout
    
    def my_view(request):
        try:
            result = request.await(my_coroutine(), timeout=3)
        except AwaitableTimeout:
            result = 'not completed'
        return {'result': result}
    
"""
import asyncio
import threading
from typing import Awaitable


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
        run_awaitable,
        'await',
    )


def run_awaitable(request, coroutine: Awaitable, timeout: int = 3):
    """
    Run a single awaitable and block until results are available or
    `timeout` seconds passes.
    
    If timeout passes then `AwaitableTimeout` exception is raised
    and the awaitable is cancelled.
    
    Example usage::
    
        from loopworker import run_awaitable, AwaitableTimeout
        
        def my_view(request):
            try:
                result = run_awaitable(request, my_coroutine(), timeout=3)
            except AwaitableTimeout:
                result = 'not completed'
            return {'result': result}
    """
    loop = request.loop

    cfuture = asyncio.run_coroutine_threadsafe(
        coroutine,
        loop
    )
    
    done, not_done = futures.wait(cfuture, timeout=timeout)
    if done:
        result = done[0].result()
    else:
        not_done[0].cancel()
        raise AwaitableTimeout('Awaitable did not complete within timeout.')
    
    return result


class LoopThread(threading.Thread):
    """Run the given event loop in a new thread."""
    
    def __init__(self, loop):
        threading.Thread.__init__(self, name='LoopThread')
        self._loop = loop

    def run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()


class AwaitableTimeout(Exception):
    """Indicates awaitable did not complete within timeout."""
    