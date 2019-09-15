import sys
from contextvars import ContextVar
from shutil import get_terminal_size
from traceback import print_exception
from contextlib import ExitStack, redirect_stdout, redirect_stderr, _RedirectStream

from .utils import lazy_property

class Run:

    def __init__(self, task, parent, retry):
        self.task = task
        self.parent = parent
        self.retry = retry
        self.n = 0

    @lazy_property
    def level(self):
        if self.parent is None:
            return 1
        return self.parent.level + 1

    @lazy_property
    def number(self):
        parent = self.parent
        return "{}{}".format(
            '' if parent is None else f'{parent.number}.{parent.n}',
            f'({self.retry})' if self.retry else '')

    def __str__(self):
        if self.parent is not None:
            return f'{self.number} {self.task}'
        return f'{self.task}'


_runner = ContextVar("runner")


class redirect_stdin(_RedirectStream):
    _stream = "stdin"


class InputWrapper:

    def __init__(self, runner, file):
        self.runner = runner
        self.file = file

    def readline(self):
        try:
            return self.file.readline()
        finally:
            self.runner.clear_status()
            self.runner.print_status()

class OutputWrapper:

    def __init__(self, runner, file):
        self.runner = runner
        self.file = file

    def write(self, s):
        self.runner.clear_status()
        self.file.write(s)
        self.file.flush()
        self.runner.print_status()

class Runner:

    def __init__(self, max_retries=0, debug=False):
        self.max_retries = max_retries
        self._token = None
        self._current = None
        self._stack = ExitStack()
        self.debug = debug

    def __enter__(self):
        assert self._token is None
        self._token = _runner.set(self)
        if not self.debug:
            self._stack.enter_context(redirect_stdin(InputWrapper(self, sys.__stdin__)))
            self._stack.enter_context(redirect_stdout(OutputWrapper(self, sys.__stdout__)))
            self._stack.enter_context(redirect_stderr(OutputWrapper(self, sys.__stderr__)))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._stack.__exit__(exc_type, exc_value, traceback)
        assert self._token is not None
        _runner.reset(self._token)

    def run(self, task):
        assert _runner.get(None) is self
        parent = self._current

        if parent is not None:
            parent.n += 1

        try:
            max_retries = self.max_retries if task.retry else 0
            self.clear_status()

            for i in range(1, max_retries + 1):
                self._current = Run(task, parent, i)
                if self.debug:
                    self.print_status_line(self._current)

                self.print_status()

                try:
                    return task()
                except Exception as e:
                    exc = sys.exc_info()
                    self.clear_status()
                    print_exception(exc[0], exc[1], exc[2].tb_next.tb_next, file=sys.__stderr__)
                    if not self.debug:
                        self.print_status_line(self._current, False)

            self._current = Run(task, parent, max_retries + 1 if max_retries else None)
            if self.debug:
                self.print_status_line(self._current)
            self.print_status()
            return task()

        finally:
            self.clear_status()

            exc = sys.exc_info()
            if isinstance(exc[0], Exception):
                print_exception(exc[0], exc[1], exc[2].tb_next.tb_next, file=sys.__stderr__)
            if not self.debug:
                self.print_status_line(self._current, exc[0] is None)
            self._current = parent
            self.print_status()

    def print_status_line(self, run, status=None, end="\n"):
        if status is None:
            status = '  '
        else:
            if not self.debug and sys.__stderr__.isatty():
                status = '\x1b[92mOK\x1b[39m' if status else '\x1b[31m!!\x1b[39m'
            else:
                status = 'OK' if status else '!!'

        run = str(run)
        if not self.debug and sys.__stderr__.isatty():
            w, _ = get_terminal_size()
            if w:
                print(f"[ {status} ] {run:{w-7}.{w-7}}", end=end, file=sys.__stderr__)
                return

        print(f"[ {status} ] {run}", end=end, file=sys.__stderr__)

    def print_status(self):
        if self.debug or self._current is None:
            return
        if not sys.__stderr__.isatty():
            return

        level = self._current.level

        print("\x1b[s\x1b[7m\x1b[1m", end='', file=sys.__stderr__)
        run = self._current
        while run is not None:
            print(file=sys.__stderr__)
            self.print_status_line(run, end="")
            run = run.parent

        print(f'\x1b[0m\x1b[u\x1b[{level}B\x1b[{level}A', end="", file=sys.__stderr__, flush=True)

    def clear_status(self):
        if self.debug or self._current is None:
            return
        if not sys.__stderr__.isatty():
            return

        print("\x1b[J", end='', file=sys.__stderr__, flush=True)
