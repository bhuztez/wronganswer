#!/usr/bin/env python3

import os
import sys

if __name__ == '__main__':
    from wronganswer.project import main
    main("Wrong Answer Project")
    quit()

SOLUTION_PATTERN = r'^(?:[^/]+)/(?P<oj>[\w\-.]+)(?:/.*)?/(?P<pid>[A-Za-z0-9_\-]+)\.c$'

def cc_argv(filename):
    yield 'clang'
    if VERBOSE:
        yield '-v'
    yield from ('-Wall','-Wextra','-Werror')
    yield from ("-x", "c")
    yield from ("-o", dest_filename(filename))
    yield "-"

def get_compile_argv(filename):
    return dest_filename(filename), list(cc_argv(filename))
