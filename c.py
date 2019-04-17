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

SOLUTION_PATTERN = r'^(?:[^/]+)/(?P<oj>[\w\-.]+)(?:/.*)?/(?P<pid>[A-Za-z0-9_\-]+)\.c$'

def cc_argv(mode, target, filename, *libs):
    yield 'clang'
    if target is not None:
        yield from ('-target', target)
    if mode == 'release':
        yield from ('-Os', '-S')
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


@task("Read source code of {filename}")
async def ReadSource(filename):
    _, (oj, pid) = get_solution_info(filename)
    source = await ReadFile(filename)
    if filename.endswith(".s"):
        env, source = await profile.asm2c(oj, pid, source)
    return source

@task("Read submission code of {name}")
async def ReadSubmission(name, recompile):
    _, (oj, pid) = get_solution_info(name)
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
