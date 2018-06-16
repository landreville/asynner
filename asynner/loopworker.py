"""
Run an asyncio loop in it's own thread for scheduling awaitables from
within Pyramid views.

This adds request property `loop` and request methods `wait_for`,
`wait_results`, and `await`.

The `loop` property returns the loop running
in it's own thread. Use this loop with `asyncio.run_coroutine_threadsafe`
to run awaitables. For example::
    
    import asyncio
    from concurrent import futures
    
    def my_view(request):
        running = asyncio.run_coroutine_threadsafe(my_coroutine(), request.loop)
        done, not_done = futures.wait([running, ...], timeout=3)
        results = [ftr.result() for ftr in done]
        return {'done': results}
    

The `wait_for` method reduces the above boiler plate by waiting for the
futures. Example usage::

    def my_view(request):
        done, not_done = request.wait_for([my_coroutine(), ...])
        results = [ftr.result() for ftr in done]
        return {'done': results}
        
The `wait_results` method reduces the boiler plate further by returning
the results after waiting. This is useful if you don't care about
unfinished tasks. Example usage::

    def my_view(request):
        results = request.wait_for([my_coroutine(), ...])
        return {'done': results}

The `await` method runs a single awaitable and
blocks until it's results are complete or timeout passes.
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
from typing import Awaitable, List, Optional, Tuple


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
    
    config.add_request_method(
        wait_for_awaitables,
        'wait_for'
    )
    
    config.add_request_method(
        wait_for_results,
        'wait_results'
    )
    
    
def wait_for_awaitables(
    request,
    awaitables: List[Awaitable],
    timeout: int = 3,
    cancel_unfinished: bool = True
) -> Tuple[List[asyncio.Future], List[asyncio.Future]]:
    """
    Wait for awaitables to complete and return tuple of finished and
    unfinished futures.
    
    If cancel_unfinished is True, any awaitables that are not complete
    by the timeout are cancelled.
    """
    running = [
        asyncio.run_coroutine_threadsafe(
            awaitable,
            loop=request.loop
        )
        for awaitable in awaitables
    ]
    
    done, not_done = futures.wait(running, timeout=timeout)
    
    if cancel_unfinished:
        for ftr in not_done:
            ftr.cancel()
    
    return done, not_done


def wait_for_results(
    request,
    awaitables: List[Awaitable],
    timeout: int = 3,
    cancel_unfinished: bool = True
) -> List[Any]:
    """
    Wait for awaitables to complete and return list of results from
    finished tasks.
    
    Note that the returned results are *not* in the same order as
    the awaitables list argument.
    
    If cancel_unfinished is True, any awaitables that are not complete
    by the timeout are cancelled.
    """
    done, not_done = wait_for_awaitables(
        request, awaitables, timeout, cancel_unfinished
    )
    
    return [ftr.result() for ftr in done]


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
    