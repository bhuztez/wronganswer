import os
import sys
from miasma import task, Command, Argument
from .profile import Profile


def _main(mod, argv):
    import logging
    logger = logging.getLogger(__package__)
    from urllib.request import urlparse

    command = mod.command
    profile = Profile()

    @task("Show input of testcase {name}")
    def input(reader, name):
        input, output = reader[name]
        print(input.read().decode(), end='')

    @task("Show output of testcase {name}")
    def output(reader, name):
        intput, output = reader[name]
        print(output.read().decode(), end='')

    @command
    @task("List testcases of {url}")
    def List(url: Argument()):
        '''list testcases'''
        oj, pid = profile.pid(url)
        reader = profile.testcases(oj, pid)
        for name in reader:
            print(name)

    @command
    @task("Show input of testcases of {url}")
    def In(url: Argument(),
           names: Argument(nargs='*')):
        '''print input'''
        oj, pid = profile.pid(url)
        reader = profile.testcases(oj, pid)
        for name in names or reader:
            input(reader, name)

    @command
    @task("Show output of testcases {names} of problem {url}")
    def Out(url: Argument(),
            names: Argument(nargs='*')):
        '''print output'''
        oj, pid = profile.pid(url)
        reader = profile.testcases(oj, pid)
        for name in names or reader:
            output(reader, name)

    @command
    @task("Test solution to problem {url}")
    def Test(url: Argument(),
             argv: Argument(nargs='+'),
             names: Argument("--only", nargs='+', required=False) = None):
        '''run test locally'''
        oj, pid = profile.pid(url)
        profile.run_tests(oj, pid, names, argv)

    @command
    @task("Submit {filename}, solution to problem {url} in {env}")
    def Submit(url: Argument(),
               agent: Argument("--agent", default='localhost'),
               env: Argument(),
               filename: Argument(nargs='?')):
        '''submit solution to online judge'''
        oj, pid = profile.pid(url)
        if filename is None or filename == '-':
            data = sys.stdin.read()
        else:
            with open(filename, 'rb') as f:
                data = f.read()

        message, extra = profile.submit(oj, pid, env, data, agent)
        logger.info("%s %s", message, filename)
        print(', '.join(f'{k}: {v}' for k, v in extra.items()))

    cmd, args = command.parse(argv)
    profile.set_debug(args.debug)
    return cmd, args


def main():
    prog = os.path.basename(sys.argv[0])
    argv = sys.argv[1:]
    command = Command(description="Wrong Answer")
    command.run(_main, argv)
