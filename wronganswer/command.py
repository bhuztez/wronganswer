import os
import sys
from types import ModuleType
from argparse import ArgumentParser
from functools import wraps
from inspect import signature
import logging

from .runner import Runner, OutputWrapper
from .task import task


def logging_color(level):
    if level >= logging.CRITICAL:
        return "31"
    elif level >= logging.ERROR:
        return "91"
    elif level >= logging.WARNING:
        return "33"
    elif level >= logging.INFO:
        return "92"
    else:
        return "94"


class Formatter(logging.Formatter):

    def formatMessage(self, record):
        if sys.__stderr__.isatty():
            record.levelname = "\x1b[7m\x1b[{}m{}\x1b[27m".format(logging_color(record.levelno), record.levelname)
            record.message = "{}\x1b[39m".format(record.message)
        return super().formatMessage(record)


def Argument(*args, **kwargs):
    return lambda dest: lambda parser: parser.add_argument(*args, dest=dest, **kwargs)

class Command:

    def __init__(self, *args, **kwargs):
        parser = ArgumentParser(*args, **kwargs)
        self._parser = parser
        self._subparsers = parser.add_subparsers(dest="COMMAND")
        self._commands = {}
        self.add_argument("--debug", action="store_true", default=False, help="turn on debug logging")
        self.add_argument("--retry", type=int, help="max number of retries")
        self.add_argument("-v", "--verbose", action="store_true", default=False, help="verbose output")
        self(self.help)

    def add_argument(self, *args, **kwargs):
        self._parser.add_argument(*args, **kwargs)

    def __call__(self, func):
        name = func.__name__.lower().replace("_", "-")
        subparser = self._subparsers.add_parser(name, help=func.__doc__)
        params = signature(func).parameters

        dests = []
        for param in params.values():
            if param.annotation == param.empty:
                continue
            param.annotation(param.name)(subparser)
            dests.append(param.name)

        @wraps(func)
        def wrapper(args):
            return func(**{d:getattr(args, d) for d in dests if getattr(args, d) is not None})

        self._commands[name] = wrapper
        return func

    def parse(self, args=None, default="help"):
        args = self._parser.parse_args(args)
        return self._commands[args.COMMAND or default], args

    @task("Print help message")
    def help(self):
        """print help message"""
        self._parser.print_help()

    def run(self, init_mod=None, argv=None):
        mod = ModuleType("__miasma__")
        mod.command = self
        mod.Argument = Argument
        mod.task = task
        mod.VERBOSE = os.environ.get("VERBOSE", "0").lower() in ("1", "on", "yes", "true")

        logging.captureWarnings(True)
        logger = logging.getLogger('')
        handler = logging.StreamHandler()
        formatter = Formatter(fmt='{levelname} {message}', style='{')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO if mod.VERBOSE else logging.WARNING)

        if init_mod is not None:
            cmd, args = init_mod(mod, argv or sys.argv[1:])
        else:
            cmd, args = self.parse(argv)

        retry = args.retry
        if retry is None:
            if 'MAX_RETRY' in os.environ:
                retry = int(os.environ['MAX_RETRY'])
            else:
                retry = getattr(mod, 'MAX_RETRY', 2)
        if args.verbose:
            mod.VERBOSE = True

        logger.setLevel(logging.INFO if mod.VERBOSE else logging.WARNING)

        with Runner(retry):
            return cmd(args)
