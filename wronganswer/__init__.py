import os
import sys
from miasma import task
from .profile import Profile
from .judge import compare_output


@task("Wrong Answer CLI")
async def _main(handler, prog, argv):
    import logging
    logger = logging.getLogger(__package__)

    from urllib.request import urlparse
    from subprocess import Popen, PIPE

    from miasma import Command, Argument

    command = Command(prog=f"{prog} URL", description="Wrong Answer")
    command.add_argument("--timestamps", action="store_true", default=False, help="show timestamp on each log line")
    command.add_argument("--debug", action="store_true", default=False, help="turn on debug logging")

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

    @task("Check against testcase {name}")
    async def test(reader, name, argv):
        input, output = reader[name]
        p = Popen(argv,stdin=PIPE,stdout=PIPE)
        got, _ = p.communicate(input.read())
        assert p.returncode == 0, "Exit code = {}".format(p.returncode)
        assert compare_output(got, output.read()), "Wrong Answer"

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
        reader = await profile.testcases(oj, pid)
        for name in names or reader:
            await test(reader, name, argv)

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

        token = await profile.submit(oj, pid, env, data, agent)
        status = None
        while status is None:
            status, message, *extra = await profile.status(oj, token, agent)
        assert status, message
        print(message)
        if extra:
            print(extra[0])

    cmd, args = command.parse(argv[1:], "list")
    if args.timestamps:
        formatter = logging.Formatter(fmt='{asctime} {message}',datefmt='%Y-%m-%d %H:%M:%S', style='{')
        handler.setFormatter(formatter)
    if args.debug:
        logger.setLevel(logging.DEBUG)
        profile.set_debug(True)

    await cmd(args)


def main(argv=sys.argv[1:]):
    import logging
    logging.captureWarnings(True)
    logger = logging.getLogger('')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    _main(handler, os.path.basename(sys.argv[0]), argv).run(retry=3)
