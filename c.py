#!/usr/bin/env python3

if __name__ == '__main__':
    from wronganswer.project import main
    main("Wrong Answer Project")
    quit()

SOLUTION_PATTERN = r'^(?:[^/]+)/(?P<oj>[\w\-.]+)(?:/.*)?/(?P<pid>[A-Za-z0-9_\-]+)\.c$'

def get_compile_argv(filename):
    dest = dest_filename(filename)
    return dest, ['gcc','-Wall','-Wextra','-Werror','-x','c','-o',dest,'-']
