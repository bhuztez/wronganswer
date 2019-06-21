#!/usr/bin/env python3

if __name__ == '__main__':
    from wronganswer.project import main
    main("Wrong Answer Project")
    quit()

import os
import platform
from wronganswer.utils import lazy_property

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
    if platform.system() == 'Linux':
        prefix = os.path.join('/usr', arch + '-w64-mingw32')
        for name in 'include', 'sys-root/mingw/include':
            yield from ('-isystem', os.path.join(prefix, name))
    elif platform.system() == 'Darwin':
        yield from ('-isystem', os.path.join(mingw.cellar, 'mingw-w64', mingw.version, 'toolchain-'+arch, arch + '-w64-mingw32', 'include'))


def cc_argv(filename, *libs, mode, target):
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
    yield from ("-o", dest_filename(filename, mode, target))
    yield "-"

def get_compile_argv(filename, *libs, mode='debug', target=None):
    dest = dest_filename(filename, mode, target)
    return dest, list(cc_argv(filename, *libs, mode=mode, target=target))

def get_submit_env(name, envs):
    return None
