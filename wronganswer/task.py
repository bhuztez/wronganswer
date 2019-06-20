from inspect import signature, BoundArguments
from functools import wraps

from .runner import _runner

class Task:
    def __init__(self, func, ba, format, retry):
        self.func = func
        self.ba = ba
        self.format = format
        self.retry = retry

    def __str__(self):
        ba = BoundArguments(self.ba._signature, self.ba.arguments)
        ba.apply_defaults()

        if self.format:
            format = self.format.format if isinstance(self.format, str) else self.format
            return format(**ba.arguments)

        return '{}({})'.format(
            self.func.__name__,
            ', '.join(
                f'{arg}={value!r}'
                for arg,value in ba.arguments.items()))

    def __call__(self):
        return self.func(*self.ba.args, **self.ba.kwargs)

def task(format=None, retry=False):

    def decorator(func):
        sig = signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            runner = _runner.get()
            try:
                return runner.run(Task(func, sig.bind(*args, **kwargs), format, retry))
            except Exception as e:
                # e = e.with_traceback(e.__traceback__.tb_next.tb_next.tb_next)
                e = e.with_traceback(None)
                raise e

        return wrapper

    return decorator
