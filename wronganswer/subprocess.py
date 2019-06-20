import sys
from shutil import which
from asyncio import ensure_future, get_event_loop
from subprocess import PIPE, STDOUT, CalledProcessError, CompletedProcess, run as _run
from asyncio.subprocess import Process, SubprocessStreamProtocol
from asyncio.streams import _DEFAULT_LIMIT

import platform
if platform.system() == 'Windows':
    from subprocess import list2cmdline as quote_argv
else:
    from pipes import quote
    def quote_argv(argv):
        return " ".join(quote(a) for a in argv)

from .runner import _runner


def run_until_complete(loop, coro):
    return loop.run_until_complete(ensure_future(coro))


class OutputReader:

    def __init__(self, file):
        self.file = file

    def feed_data(self, data):
        self.file.write(data.decode())

    def feed_eof(self):
        pass

    def set_exception(self, exc):
        pass


class CaptureOutputProtocol(SubprocessStreamProtocol):

    def __init__(self, stdout, stderr, limit, loop):
        super().__init__(limit, loop)
        self._stdout = stdout
        self._stderr = stderr

    def connection_made(self, transport):
        super().connection_made(transport)
        if self._stdout is None:
            self.stdout = OutputReader(sys.stdout)
        if self._stderr is None:
            self.stderr = OutputReader(sys.stderr)
        if self._stderr is STDOUT:
            self.stderr = OutputReader(sys.stdout)


class Subprocess(Process):

    def __init__(self, transport, protocol, loop):
        super().__init__(transport, protocol, loop)

    async def communicate(self, input=None):
        if self._protocol._stdout is None:
            self.stdout = None
        if self._protocol._stderr is None:
            self.stderr = None
        return await super().communicate(input)


def run(args, executable=None, stdin=None, stdout=None, stderr=None, input=None, capture_output=False, check=False, shell=False, **kwargs):
    runner = _runner.get()

    if stdin is None and input is None:
        runner.clear_status()
        try:
            if capture_output:
                return _run(args, executable=executable, capture_output=True, check=check, shell=shell, **kwargs)
            else:
                return _run(args, executable=executable, stdout=stdout, stderr=stderr, check=check, shell=shell, **kwargs)
        finally:
            runner.print_status()

    if input is not None:
        stdin = PIPE

    if capture_output:
        stdout = PIPE
        stderr = PIPE

    loop = get_event_loop()

    factory = lambda: CaptureOutputProtocol(stdout, stderr, limit=_DEFAULT_LIMIT, loop=loop)

    if shell:
        executable = None
        creator = lambda **kwargs: loop.subprocess_shell(factory, quote_argv(args), **kwargs)
    else:
        if executable is None:
            executable = which(args[0])
            args = args[1:]
        creator = lambda **kwargs: loop.subprocess_exec(factory, executable, *args, **kwargs)

    transport, protocol = run_until_complete(loop, creator(stdin=stdin, stdout=stdout or PIPE, stderr=PIPE if stderr in (None, STDOUT) else stderr, **kwargs))
    p = Subprocess(transport, protocol, loop)

    try:
        stdout, stderr = run_until_complete(loop, p.communicate(input))
    except:
        p.kill()
        raise

    retcode = p.returncode
    if executable is not None:
        args = [executable] + list(args)
    if check and retcode:
        raise CalledProcessError(retcode, quote_argv(args), output=stdout, stderr=stderr)
    return CompletedProcess(args, retcode, stdout, stderr)
