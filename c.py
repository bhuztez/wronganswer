#!/usr/bin/env python3

if __name__ == '__main__':
    import sys
    import os

    try:
        import miasma
    except ImportError:
        ROOT=os.path.dirname(os.path.abspath(__file__))
        sys.path.append(os.path.dirname(ROOT)+"/miasma")

    from wronganswer.project import main
    main("Wrong Answer Project")
    quit()

import os
import sys

SOLUTION_PATTERN = r'^(?:[^/]+)/(?P<oj>[\w\-.]+)(?:/.*)?/(?P<pid>[A-Za-z0-9_\-]+)\.c$'

def mingw_include(target):
    if 'windows' not in target:
        return
    arch = target.split('-', 1)[0]
    if sys.platform == 'linux':
        prefix = os.path.join('/usr', arch + '-w64-mingw32')
        for name in 'include', 'sys-root/mingw/include':
            yield from ('-isystem', os.path.join(prefix, name))
    elif sys.platform == 'darwin':
        import json
        info = json.loads(subprocess.check_output(["brew", "info", "--json=v1", "mingw-w64"]))[0]
        cellar = info["bottle"]["stable"]["cellar"]
        version = info["linked_keg"]
        yield ('-isystem', os.path.join(cellar, 'mingw-w64', version, 'toolchain-'+arch, arch + '-w64-mingw32', 'include'))


def cc_argv(mode, target, filename, *libs):
    yield 'clang'
    if target is not None:
        yield from ('-target', target)
    if mode == 'release':
        yield from ('-Os', '-S')
    if VERBOSE:
        yield '-v'
    yield from mingw_include(target)
    yield from ('-Wall','-Wextra','-Werror')
    yield from ("-x", "c")
    yield from ("-o", dest_filename(mode, target, filename))
    yield "-"

def get_compile_argv(mode, target, filename, *libs):
    if filename.endswith(".s"):
        dest = filename[:-2] + ".elf"
        return filename[:-2] + ".elf", ('gcc', '-o', dest, '-x', 'c', '-'), None

    env = os.environ.copy()
    dest = dest_filename(mode, target, filename)
    return dest, list(cc_argv(mode, target, filename, *libs)), env

def get_run_argv(filename):
    return (os.path.join(ROOTDIR, filename),)


@task("Read submission code of {name}")
async def ReadSubmission(name, recompile):
    oj, pid = get_solution_info(name)
    target = profile.asm_llvm_target(oj)
    asm = await Compile(name, recompile, mode='release', target=target)
    source = await ReadFile(asm)
    env, source = await profile.asm2c(oj, pid, source)
    return env, source


command(Compile)
command(Run)
command(Test)
command(Preview)
command(Submit)
command(Clean)
