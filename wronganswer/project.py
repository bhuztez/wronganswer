import os
import sys
import logging
import platform
from .asm import escape_source
from .command import Command, Argument
from .profile import Profile
logger = logging.getLogger(__package__)

def index_of(l, x):
    try:
        return l.index(x)
    except ValueError:
        return len(l)

def asm_pick_env(envs):
    envs = [c for c in envs
            if c.lang == "C" and c.name in ("GCC", "MinGW")]
    envs.sort(key=lambda c:
              (index_of(['Linux','Windows'], c.os),
               index_of(['x86_64','x86'], c.arch)))
    return envs[0]

def llvm_target(env):
    return "{}-{}-gnu".format(
        {"x86": "i686", "x86_64": "x86_64"}[env.arch],
        {"Windows": "pc-windows", "Linux": "unknown-linux"}[env.os])

EXTS = {
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".cxx": "C++",
    ".d": "D",
    ".for": "Fortran",
    ".hs": "Haskell",
    ".go": "Go",
    ".java": "Java",
    ".js": "ECMAScript",
    ".kt": "Kotlin",
    ".ml": "OCaml",
    ".pas": "Pascal",
    ".php": "PHP",
    ".py": "Python3",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sc": "Scala",
    ".swift": "Swift",
}

def guess_language(name):
    _, ext = os.path.splitext(name)
    return EXTS[ext]

SUFFIX = ".elf"
if platform.system() == 'Windows':
    SUFFIX = ".exe"


def init(command, profile, cfg):
    __all__ = (
        'ROOTDIR', 'SOLUTIONS_DIR',
        'target_dir', 'dest_filename',
        'find_solutions', 'get_solution_info',
        'compile_libs', 'get_compile_argv', 'read_source',
        'get_run_argv', 'get_submit_env', 'clean_solution')

    import re
    from .subprocess import run as call, quote_argv
    from .task import task

    def target_dir(mode, target):
        yield 'target'
        if target is not None:
            yield target
        yield mode

    def dest_filename(filename, mode='debug', target=None):
        basename = os.path.splitext(os.path.basename(filename))[0]
        basename += ".s" if mode == 'release' else SUFFIX
        return os.path.join(os.path.dirname(filename), *cfg.target_dir(mode, target), basename)

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
            filename = os.path.relpath(filename, basedir)

        if os.sep != '/':
            filename = filename.replace(os.sep, '/')
        return filename

    ROOTDIR = os.path.dirname(os.path.abspath(cfg.__file__))
    SOLUTIONS_DIR = os.path.join(ROOTDIR, "solutions")

    def get_run_argv(filename):
        return (os.path.join(cfg.ROOTDIR, filename),)

    def get_solution_info(filename):
        m = re.match(cfg.SOLUTION_PATTERN, filename)
        if m is None:
            return None
        return m.group('oj'), m.group('pid')

    def find_solutions(filename=None):
        if filename is None:
            filename = cfg.SOLUTIONS_DIR
        filename = os.path.abspath(filename)
        if os.path.isdir(filename):
            for root,dirs,files in os.walk(filename):
                for name in files:
                    fullname = relative_path(cfg.ROOTDIR, os.path.join(root,name))
                    info = cfg.get_solution_info(fullname)
                    if info:
                        yield fullname, info
        else:
            fullname = relative_path(cfg.ROOTDIR, filename)
            info = cfg.get_solution_info(fullname)
            if info:
                yield fullname, info

    @task("Read source of {filename}")
    def read_source(filename):
        with open(filename, 'rb') as f:
            return f.read()

    def compile_libs(mode='debug', target=None):
        return ()

    def _compile(filename, recompile, mode='debug', target=None, escape=False):
        kwargs = {}
        if mode != 'debug' or target is not None:
            kwargs['mode'] = mode
            kwargs['target'] = target

        libs = cfg.compile_libs(**kwargs)
        if not escape:
            dest, argv, *env = cfg.get_compile_argv(filename, *libs, **kwargs)
            if len(env) == 0:
                env = None
            else:
                env = env[0]
        else:
            assert filename.endswith(".s")
            dest = filename[:-2] + SUFFIX
            argv = ('gcc', '-o', dest, '-x', 'c', '-', '-lm')
            env = None

        if dest == filename:
            return filename

        if not (recompile or has_to_recompile(dest, filename, *libs)):
            return dest

        if not escape:
            source = cfg.read_source(filename)
        else:
            source = escape_source(read_source(filename))

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        call(argv, input=source, check=True)
        return dest

    @command
    @task("Compile {filename}")
    def compile(filename: Argument(help="path to solution"),
                recompile: Argument("-r", "--recompile", action="store_true", help="force recompile") = False,
                mode = 'debug',
                target = None):
        '''compile solution'''
        dest = _compile(filename, recompile, mode, target)
        if mode == 'release' and target is None:
            dest = _compile(dest, recompile, mode, target, True)
        return dest

    @task("Test {filename}")
    def test_solution(oj, pid, filename, recompile, mode='debug', names=None, target=None, rootdir=None):
        path = os.path.join(rootdir or cfg.ROOTDIR, filename)
        executable = compile(path, recompile, mode, target)
        profile.run_tests(oj, pid, names, cfg.get_run_argv(executable))

    def get_submit_env(name, envs):
        lang = guess_language(name)
        envs = [e for e in envs if e.lang == lang]
        import platform
        if platform.system() == 'Windows':
            o = ['Windows', 'Linux']
        else:
            o = ['Linux', 'Windows']
        envs.sort(key = lambda e: index_of(o, e.os))
        return envs[0]

    @task("Read submission code of {filename}")
    def read_submission(filename, recompile, rootdir=None):
        oj, pid = cfg.get_solution_info(filename)
        envs = profile.get_envs(oj)
        env = cfg.get_submit_env(filename, envs)
        path = os.path.join(rootdir or cfg.ROOTDIR, filename)

        if env is not None:
            return env.code, cfg.read_source(path)

        env = asm_pick_env(envs)
        target = llvm_target(env)
        asm = compile(path, recompile, mode='release', target=target)
        source = read_source(asm)
        prologue = profile.prologue(oj, pid)
        return env.code, prologue + escape_source(source)

    @task("Remove {filename}")
    def remove_file(filename, rootdir=None):
        path = os.path.join(rootdir or cfg.ROOTDIR, filename)
        if os.path.isdir(path):
            from shutil import rmtree
            rmtree(path, ignore_errors=True)
        else:
            os.remove(path)

    @task("Clean {filename}")
    def clean_solution(filename, rootdir=None):
        from glob import escape, iglob
        path = os.path.join(rootdir or cfg.ROOTDIR, filename)
        dirname = escape(os.path.join(os.path.dirname(path), "target"))
        basename = escape(os.path.splitext(os.path.basename(path))[0])

        for filename in iglob(f"{dirname}/**/{basename}.*", recursive=True):
            remove_file(filename)

    @command
    @task("Run {filename}")
    def run(filename: Argument(help="path to solution"),
            recompile: Argument("-r", "--recompile", action="store_true", help="force recompile") = False):
        '''build solution'''
        executable = compile(filename, recompile)
        argv = cfg.get_run_argv(executable)
        call(argv)

    @command
    @task("Test")
    def test(filename: Argument(nargs='?', help="path to solution") = None,
             recompile: Argument("-r", "--recompile", action="store_true", help="force recompile") = False,
             mode: Argument("--mode") = 'debug',
             names: Argument("--only", nargs='+', required=False) = None):
        '''check solution against sample testcases'''
        for name, (oj, pid) in cfg.find_solutions(filename):
            test_solution(oj, pid, name, recompile, mode, names)

    @command
    @task("List of testcases")
    def List(filename: Argument(help="path to solution")):
        '''list testcases'''
        filename = relative_path(cfg.ROOTDIR, filename)
        oj, pid = cfg.get_solution_info(filename)
        reader = profile.testcases(oj, pid)
        for name in reader:
            print(name)

    @command
    @task("Input of testcase")
    def In(filename: Argument(help="path to solution"),
           names: Argument(nargs='*')):
        '''print input'''
        filename = relative_path(cfg.ROOTDIR, filename)
        oj, pid = cfg.get_solution_info(filename)
        reader = profile.testcases(oj, pid)
        for name in names or reader:
            input, output = reader[name]
            print(input.read().decode(), end='')

    @command
    @task("Output of testcase")
    def Out(filename: Argument(help="path to solution"),
           names: Argument(nargs='*')):
        '''print output'''
        filename = relative_path(cfg.ROOTDIR, filename)
        oj, pid = cfg.get_solution_info(filename)
        reader = profile.testcases(oj, pid)
        for name in names or reader:
            input, output = reader[name]
            print(output.read().decode(), end='')

    @command
    @task("Preview submission of {filename}")
    def preview(filename: Argument(help="path to solution"),
                recompile: Argument("-r", "--recompile", action="store_true", help="force recompile") = False):
        '''preview the code to be submitted'''
        filename = relative_path(cfg.ROOTDIR, filename)
        oj, pid = cfg.get_solution_info(filename)
        env, code = read_submission(filename, recompile)
        print(code.decode())

    @command
    @task("Submit")
    def submit(filename: Argument(nargs='?', help="path to solution") = None,
               agent: Argument("--agent", default='localhost') = 'localhost',
               recompile: Argument("-r", "--recompile", action="store_true", help="force recompile") = False):
        '''submit solution'''
        for name, (oj, pid) in cfg.find_solutions(filename):
            env, code = read_submission(name, recompile)
            message, extra = profile.submit(oj, pid, env, code, agent)
            logger.info("%s %s", message, name)
            print(extra)

    @command
    @task("Clean")
    def clean(filename: Argument(nargs='?', help="path to solution") = None):
        """removes generated files"""

        for name,info in cfg.find_solutions(filename):
            cfg.clean_solution(name)

    return cfg.__dict__.update(
        {k:v
         for k, v in locals().items()
         if k in __all__})


class WrongAnswerProject(Command):

    def __init__(self, description):
        super().__init__(description=description)

    def init_mod(self, mod, argv):
        profile = Profile()

        __main__ = sys.modules['__main__']
        filename = __main__.__file__
        mod.__file__ = filename
        mod.profile = profile

        init(self.add_command, profile, mod)

        with open(filename, 'r') as f:
            code = compile(f.read(), filename, 'exec')
        exec(code, mod.__dict__)

        cmd, args = super().init_mod(mod, argv)
        profile.set_debug(args.debug)
        return cmd, args

def main(description, argv=None):
    main = WrongAnswerProject(description)
    main(argv)
