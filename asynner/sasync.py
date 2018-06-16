"""
Tools for working with async futures from synchronous code.

Provides similar functions to concurrent.futures, but for
asyncio futures.
"""
import asyncio
import logging
from typing import Union, List, Awaitable, Optional, Set
from threading import Event
from concurrent.futures import Future as ConcurrentFuture
from asyncio.futures import Future as AsyncFuture


log = logging.getLogger(__name__)


def unwrap_future(ftr: Awaitable):
    """
    Wrap an asyncio.futures.Future in a concurrent.futures.Future
    
    Essentially the opposite of asyncio.wrap_future.
    """
    ftr = asyncio.ensure_future(ftr)
    new_future = ConcurrentFuture()
    # The docs say not to use concurrent.futures.Future.set_result
    # but the only alternative would be running the asyncio future on the
    # event loop while waiting on a concurrent future in a thread worker.
    # That would block a thread worker for no reason.
    ftr.add_done_callback(
        lambda ftr: new_future.set_result(ftr.result())
    )
    return new_future


def wait(tasks: Union[Awaitable, List[Awaitable]], timeout: Optional[int] = None):
    """
    Wait for all tasks to complete or timeout.
    
    Returns a two-tuple of (completed futures, uncompleted futures).
    
    Example usage::
    
        multiple_tasks = [my_coroutine(el) for el in my_list]
        done, not_done = sasync.wait(multiple_tasks, timeout=3)
        results = [ftr.result() for ftr in done]
    
    """
    policy = asyncio.get_event_loop_policy()
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        print('Creating new event loop')
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if not isinstance(tasks, list):
        tasks = [tasks]
    return Waiter(tasks, timeout).wait()


class Waiter(object):
    """Implements a blocking wait for a awaitables to compete."""
    
    def __init__(self, tasks: List[Awaitable], timeout: Optional[int] = None):
        self._tasks: Set[AsyncFuture] = {
            asyncio.ensure_future(task) for task in set(tasks)
        }
        self._num_pending = len(tasks)
        self._completed: Set[AsyncFuture] = set()
        self._event = Event()
        self._timeout = timeout
        
    def wait(self):
        """
        Wait for given awaitables to complete and return a tuple with
        two sets: (completed awaitables, uncomplete awaitables).
        """
        for i, task in enumerate(self._tasks):
            task.add_done_callback(self.done)
            
        # TODO: can't block I think
        complete = self._event.wait(timeout=self._timeout)
        
        import pdb; pdb.set_trace()
        
        for task in self._tasks:
            if task not in self._completed:
                task.cancel()
        
        return self._completed, self._tasks - self._completed
        
    def done(self, ftr: AsyncFuture):
        """Flag the given future as complete."""
        log.debug(f'Completed future: {ftr}.')
        self._completed.add(ftr)
        self._num_pending -= 1
        
        if self._num_pending <= 0:
            self._event.set()
        
    