import sys
from .asm import escape_source

def init(cfg):
    __all__ = ('target_dir', 'dest_filename', 'ROOTDIR', 'SOLUTIONS_DIR', 'profile', 'get_solution_info', 'find_solutions', 'ReadFile', 'ReadSource', 'RemoveOutput', 'RemoveFile', 'Call', 'CompileLibs', 'Compile', 'Run', 'Test', 'TestSolution', 'Preview', 'Submit', 'SubmitSolution', 'Clean')

    import os
    import re
    from miasma.subprocess import run, quote_argv
    import logging
    from .profile import Profile

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
        m = re.match(cfg.SOLUTION_PATTERN, filename)
        if m is None:
            return None
        return m.group('oj'), m.group('pid')

    def find_solutions(filename=None):
        if filename is None:
            filename = cfg.SOLUTIONS_DIR
        if os.path.isdir(filename):
            for root,dirs,files in os.walk(filename):
                for name in files:
                    fullname = relative_path(cfg.ROOTDIR, os.path.join(root,name))
                    info = cfg.get_solution_info(fullname)
                    if info:
                        yield fullname, info
        else:
            fullname = relative_path(cfg.ROOTDIR, filename)
            info = cfg.get_solution_info(filename)
            if info:
                yield fullname, info

    command = cfg.command
    task = cfg.task
    profile = Profile()

    @task("Read {filename}")
    def ReadFile(filename):
        with open(filename, 'rb') as f:
            return f.read()

    def Call(argv, *args, **kwargs):
        logger.debug("Running `{}`".format(quote_argv(argv)))
        return run(argv, *args, **kwargs)

    ReadSource = ReadFile

    def CompileLibs(mode='debug', target=None):
        return ()

    def _compile(filename, recompile, mode, target, escape=False):
        libs = cfg.CompileLibs(mode, target)
        dest, argv, env = cfg.get_compile_argv(mode, target, filename, *libs)
        if dest == filename:
            return filename

        if not (recompile or has_to_recompile(dest, filename, *libs)):
            return dest

        source = cfg.ReadSource(filename)
        if escape:
            source = escape_source(source)

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        Call(argv, input=source, check=True)
        return dest

    @task("Compile {filename}")
    def Compile(filename: cfg.Argument(help="path to solution"),
                      recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False,
                      mode = 'debug',
                      target = None):
        '''compile solution'''
        dest = _compile(filename, recompile, mode, target)
        if mode == 'release' and target is None:
            dest = _compile(dest, recompile, mode, target, True)
        return dest

    @task("Run {filename}")
    def Run(filename: cfg.Argument(help="path to solution"),
                  recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False):
        '''build solution'''
        executable = cfg.Compile(filename, recompile)
        argv = cfg.get_run_argv(executable)
        Call(argv)

    @task("Test {filename}")
    def TestSolution(oj, pid, filename, recompile, mode='debug', target=None):
        executable = cfg.Compile(filename, recompile, mode, target)
        profile.run_tests(oj, pid, [], cfg.get_run_argv(executable))

    @task("Test")
    def Test(filename: cfg.Argument(nargs='?', help="path to solution") = None,
                   recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False,
                   mode: cfg.Argument("--mode") = 'debug'):
        '''check solution against sample testcases'''
        for name, (oj, pid) in find_solutions(filename):
            cfg.TestSolution(oj, pid, name, recompile, mode)

    @task("Preview {filename}")
    def Preview(filename: cfg.Argument(help="path to solution"),
                      recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False):
        '''preview the code to be submitted'''
        filename = relative_path(cfg.ROOTDIR, filename)
        oj, pid = cfg.get_solution_info(filename)
        env, code = cfg.ReadSubmission(filename, recompile)
        print(code.decode())

    @task("Submit {name}")
    def SubmitSolution(oj, pid, name, agent, recompile):
        env, code = cfg.ReadSubmission(name, recompile)
        message, extra = profile.submit(oj, pid, env, code, agent)
        logger.info("%.0s %s", message, name)
        print(extra)

    @task("Submit")
    def Submit(filename: cfg.Argument(nargs='?', help="path to solution") = None,
                     agent: cfg.Argument("--agent", default='localhost') = 'localhost',
                     recompile: cfg.Argument("-r", "--recompile", action="store_true", help="force recompile") = False):
        '''submit solution'''
        for name, (oj, pid) in find_solutions(filename):
            SubmitSolution(oj, pid, name, agent, recompile)

    @task("Remove {filename}")
    def RemoveFile(filename, rootdir=None):
        path = os.path.join(rootdir or cfg.ROOTDIR, filename)
        if os.path.isdir(path):
            from shutil import rmtree
            rmtree(path, ignore_errors=True)
        else:
            os.remove(path)

    @task("Remove {filename}")
    def RemoveOutput(filename, rootdir=None):
        from glob import escape, iglob
        dirname = escape(os.path.join(os.path.dirname(filename), "target"))
        basename = escape(os.path.splitext(os.path.basename(filename))[0])

        for filename in iglob(f"{dirname}/**/{basename}.*", recursive=True):
            cfg.RemoveFile(filename)

    @task("Clean")
    def Clean(filename:cfg.Argument(nargs='?', help="path to solution") = None):
        """removes generated files"""

        for name,info in find_solutions(filename):
            cfg.RemoveOutput(name)

    return cfg.__dict__.update(
        {k:v
         for k, v in locals().items()
         if k in __all__})


def _main(mod, argv):
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
