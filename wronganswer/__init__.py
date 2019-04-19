import os
import sys
from miasma import task, Command, Argument
from .profile import Profile


async def _main(mod, argv):
    import logging
    logger = logging.getLogger(__package__)

    from urllib.request import urlparse

    command = mod.command

    profile = Profile()
    if not argv:
        await command.help()
        quit(1)

    oj = urlparse(argv[0]).netloc
    try:
        pid = await profile.pid(argv[0])
    except Exception:
        logger.exception("")
        await command.help()
        quit(1)

    @task("Show input of testcase {name}")
    async def input(reader, name):
        input, output = reader[name]
        print(input.read().decode(), end='')

    @task("Show output of testcase {name}")
    async def output(reader, name):
        intput, output = reader[name]
        print(output.read().decode(), end='')

    @command
    @task(f"List testcases of problem {pid} of {oj}")
    async def List():
        '''list testcases'''
        reader = await profile.testcases(oj, pid)
        for name in reader:
            print(name)

    @command
    @task(f"Show input of testcases of problem {pid} of {oj}")
    async def In(names: Argument(nargs='*')):
        '''print input'''
        reader = await profile.testcases(oj, pid)
        for name in names or reader:
            await input(reader, name)

    @command
    @task(f"Show output of testcases {{names}} of problem {pid} of {oj}")
    async def Out(names: Argument(nargs='*')):
        '''print output'''
        reader = await profile.testcases(oj, pid)
        for name in names or reader:
            await output(reader, name)

    @command
    @task(f"Test solution to problem {pid} of {oj}")
    async def Test(argv: Argument(nargs='+'),
             names: Argument("--only", nargs='+', required=False) = None):
        '''run test locally'''
        await profile.run_tests(oj, pid, names, argv)

    @command
    @task(f"Submit {{filename}}, solution to problem {pid} in {{env}}, to {oj}")
    async def Submit(agent: Argument("--agent", default='localhost'),
               env: Argument(),
               filename: Argument(nargs='?')):
        '''submit solution to online judge'''
        if filename is None or filename == '-':
            data = sys.stdin.read()
        else:
            with open(filename, 'rb') as f:
                data = f.read()

        message, extra = await profile.submit(oj, pid, env, data, agent)
        logger.info("%.0s %s", message, filename)
        print(extra)

    cmd, args = command.parse(argv[1:], "list")
    profile.set_debug(args.debug)
    return cmd, args


def main():
    prog = os.path.basename(sys.argv[0])
    argv = sys.argv[1:]
    command = Command(prog=f"{prog} URL", description="Wrong Answer")
    command.run(_main, argv)
