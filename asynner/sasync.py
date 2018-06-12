"""
Tools for working with async futures from synchronous code.

Provides similar functions to concurrent.futures, but for
asyncio futures.
"""
from threading import Event
from concurrent import futures


def unwrap_future(future):
    """Wrap an asyncio.futures.Future in a concurrent.futures.Future"""
    new_future = futures.Future()
    future.add_done_callback(
        lambda ftr: new_future.set_result(ftr.result())
    )
    return new_future


def wait(tasks, timeout=None):
    """
    Wait for all tasks to complete or after timeout.
    
    Returns a two-tuple of (completed futures, uncompleted futures)
    """
    if not isinstance(tasks, list):
        tasks = [tasks]
    return Waiter(tasks, timeout).wait()


class Waiter(object):
    
    def __init__(self, tasks, timeout=None):
        self._tasks = set(tasks)
        self._num_pending = len(tasks)
        self._completed = set()
        self._event = Event()
        self._timeout = timeout
        
    def wait(self):
        for i, task in enumerate(self._tasks):
            task.add_done_callback(self.done)
            
        complete = self._event.wait(timeout=self.timeout)
        
        for task in self._tasks:
            task.cancel()
        
        return self._completed, self._tasks - self._completed
        
        
    def done(self, ftr):
        self._completed.add(ftr)
        self._num_pending -= 1
        
        if self._num_pending <= 0:
            self._event.set()
        
    