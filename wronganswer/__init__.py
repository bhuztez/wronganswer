import os
import sys
import logging
from .task import task
from .command import Command, Argument
from .profile import Profile

logger = logging.getLogger(__package__)

class WrongAnswer(Command):

    def __init__(self):
        super().__init__(description="Wrong Answer")

    def init_mod(self, mod, argv):
        command = self.add_command
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
        @task("List environment")
        def Env(oj: Argument()):
            '''list environments'''
            for env in profile.get_envs(oj):
                print(env)

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

        cmd, args = super().init_mod(mod, argv)
        profile.set_debug(args.debug)
        return cmd, args

main = WrongAnswer()
