import sys

def init(cfg):
    __all__ = ('target_dir', 'dest_filename', 'ROOTDIR', 'SOLUTIONS_DIR', 'profile', 'get_solution_info', 'find_solutions', 'ReadFile', 'ReadSource', 'RemoveOutput', 'RemoveFile', 'Call', 'CheckOutput', 'CompileLibs', 'Compile', 'Run', 'Test', 'TestSolution', 'Preview', 'Submit', 'SubmitSolution', 'Status', 'Clean')

    import os
    import re
    from subprocess import Popen, PIPE, check_call, check_output
    import logging
    from .profile import quote_argv, Profile

    logger = logging.getLogger(__package__)

    def target_dir(mode, target):
        yield 'target'
        if target is not None:
            yield target
        else:
            yield mode

    def dest_filename(mode, target, filename):
        basename = os.path.splitext(os.path.basename(filename))[0]
        basename += ".s" if mode == 'release' else ".elf"
        return os.path.join(os.path.dirname(filename), *target_dir(mode, target), basename)

    def has_to_recompile(dest, *sources):
        if not os.path.exists(dest):
            return True

        for source in sources:
            if os.stat(source).st_mtime >= os.stat(dest).st_mtime:
                return True
        return False

    def relative_path(basedir, filename):
        basedir = os.path.abspath(basedir)
        filename = os.path.abspath(filename)

        if os.path.commonprefix([filename,basedir]) == basedir:
            return os.path.relpath(filename, basedir)
        else:
            return filename

    ROOTDIR = os.path.dirname(os.path.abspath(cfg.__file__))
    SOLUTIONS_DIR = os.path.join(ROOTDIR, "solutions")

    def get_solution_info(filename):
        name = relative_path(cfg.ROOTDIR, filename)
        m = re.match(cfg.SOLUTION_PATTERN, name)
        if m is None:
            return None
        return name, (m.group('oj'), m.group('pid'))

    def find_solutions(filename=None):
        if filename is None:
            filename = cfg.SOLUTIONS_DIR
        if os.path.isdir(filename):
            for root,dirs,files in os.walk(filename):
                for name in files:
                    fullname = os.path.join(root,name)
                    info = cfg.get_solution_info(fullname)
                    if info:
                        yield info
        else:
            info = cfg.get_solution_info(filename)
            if info:
                yield info

    command = cfg.command
    task = cfg.task
    profile = Profile()

    @task("Read {filename}")
    async def ReadFile(filename):
        with open(filename, 'rb') as f:
            return f.read()

    async def Call(argv, *args, **kwargs):
        logger.debug(quote_argv(argv))
        return check_call(argv, *args, **kwargs)

    async def CheckOutput(argv, *args, **kwargs):
        if cfg.VERBOSE:
            print(quote_argv(argv))
        return check_output(argv, *args, **kwargs)

    ReadSource = ReadFile

    @task()
    async def CompileLibs(mode='debug', target=None):
        return ()

    async def _compile(filename, recompile, mode, target):
        libs = await cfg.CompileLibs(mode, target)
        dest, argv, env = cfg.get_compile_argv(mode, target, filename, *libs)
        if dest == filename:
            return filename

        if not (recompile or has_to_recompile(dest, filename, *libs)):
            return dest

        source = await cfg.ReadSource(filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        logger.debug(quote_argv(argv))
        proc = Popen(argv,stdin=PIPE,env=env)
        proc.communicate(source)
        assert proc.returncode == 0
        return dest

    @task("Compile {filename}")
    async def Compile(filename: cfg.Argument(help="path to solution"),
                      recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False,
                      mode = 'debug',
                      target = None):
        '''compile solution'''
        dest = await _compile(filename, recompile, mode, target)
        if mode == 'release' and target is None:
            dest = await _compile(dest, recompile, mode, target)
        return dest

    @task("Run {filename}")
    async def Run(filename: cfg.Argument(help="path to solution"),
                  recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False):
        '''build solution'''
        executable = await cfg.Compile(filename, recompile)
        argv = cfg.get_run_argv(executable)
        await cfg.Call(argv)

    @task()
    async def TestSolution(oj, pid, filename, recompile, mode='debug', target=None):
        executable = await cfg.Compile(filename, recompile, mode, target)
        reader = await profile.testcases(oj, pid)
        for name in reader:
            await profile.run_test(oj, pid, name, cfg.get_run_argv(executable))

    @task()
    async def Test(filename: cfg.Argument(help="path to solution"),
                   recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False,
                   mode: cfg.Argument("--mode") = 'debug'):
        '''check solution against sample testcases'''
        for name, (oj, pid) in find_solutions(filename):
            await cfg.TestSolution(oj, pid, name, recompile, mode)

    @task("Preview {filename}")
    async def Preview(filename: cfg.Argument(help="path to solution"),
                      recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False):
        '''preview the code to be submitted'''
        name, (oj, pid) = cfg.get_solution_info(filename)
        env, code = await cfg.ReadSubmission(name, recompile)
        print(code.decode())

    @task("Submit {filename}")
    async def Submit(filename: cfg.Argument(help="path to solution"),
                     agent: cfg.Argument("--agent", default='localhost'),
                     recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False):
        '''submit solution'''
        for name, (oj, pid) in find_solutions(filename):
            env, code = await cfg.ReadSubmission(name, recompile)
            message, extra = await profile.submit(oj, pid, env, code, agent)
            print(message)
            print(extra)

    @task("Remove {filename}")
    async def RemoveFile(filename, rootdir=None):
        os.remove(os.path.join(rootdir or cfg.ROOTDIR, filename))

    @task("Remove {filename}", level=logging.DEBUG)
    async def RemoveOutput(filename, rootdir=None):
        from glob import escape, iglob
        dirname = escape(os.path.join(os.path.dirname(filename), "target"))
        basename = escape(os.path.splitext(os.path.basename(filename))[0])

        for filename in iglob(f"{dirname}/**/{basename}.*", recursive=True):
            await cfg.RemoveFile(filename)

    @task("Clean")
    async def Clean(filename:cfg.Argument(nargs='?', help="path to solution")=None):
        """removes generated files"""

        for name,info in find_solutions(filename):
            await cfg.RemoveOutput(name)

    return cfg.__dict__.update(
        {k:v
         for k, v in locals().items()
         if k in __all__})


async def _main(mod, argv):
    command = mod.command
    __main__ = sys.modules['__main__']
    filename = __main__.__file__
    mod.__file__ = filename

    init(mod)
    with open(filename, 'r') as f:
        code = compile(f.read(), filename, 'exec')
    exec(code, mod.__dict__)

    cmd, args = command.parse()
    mod.profile.set_debug(args.debug)
    return cmd, args


def main(description, argv=None):
    from miasma import Command
    command = Command(description=description)
    command.run(_main, argv)
