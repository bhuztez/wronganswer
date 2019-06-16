#!/usr/bin/env python3

import os
import sys

if __name__ == '__main__':
    try:
        import miasma
    except ImportError:
        ROOT=os.path.dirname(os.path.abspath(__file__))
        sys.path.append(os.path.dirname(ROOT)+"/miasma")

    from wronganswer.project import main
    main("Wrong Answer Project")
    quit()

from miasma.utils import lazy_property

SOLUTION_PATTERN = r'^(?:[^/]+)/(?P<oj>[\w\-.]+)(?:/.*)?/(?P<pid>[A-Za-z0-9_\-]+)\.c$'

class BrewPackage:
    def __init__(self, package):
        self.package = package

    @lazy_property
    def info(self):
        import json, subprocess
        info = json.loads(subprocess.check_output(["brew", "info", "--json=v1", self.package]))[0]
        cellar = info["bottle"]["stable"]["cellar"]
        version = info["linked_keg"]
        return cellar, version

    @property
    def cellar(self):
        return self.info[0]

    @property
    def version(self):
        return self.info[1]

mingw = BrewPackage("mingw-w64")

class Clang:

    @lazy_property
    def has_addrsig(self):
        import subprocess
        info = subprocess.check_output(["clang", "--help"])
        return b'addrsig' in info

clang = Clang()

def mingw_include(target):
    if target is None or 'windows' not in target:
        return
    arch = target.split('-', 1)[0]
    if sys.platform == 'linux':
        prefix = os.path.join('/usr', arch + '-w64-mingw32')
        for name in 'include', 'sys-root/mingw/include':
            yield from ('-isystem', os.path.join(prefix, name))
    elif sys.platform == 'darwin':
        yield from ('-isystem', os.path.join(mingw.cellar, 'mingw-w64', mingw.version, 'toolchain-'+arch, arch + '-w64-mingw32', 'include'))


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
    if clang.has_addrsig:
        yield '-fno-addrsig'
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
def ReadSubmission(name, recompile):
    oj, pid = get_solution_info(name)
    target = profile.asm_llvm_target(oj)
    asm = Compile(name, recompile, mode='release', target=target)
    source = ReadFile(asm)
    env, source = profile.asm2c(oj, pid, source)
    return env, source

command(Compile)
command(Run)
command(Test)
command(Preview)
command(Submit)
command(Clean)
