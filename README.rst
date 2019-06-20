===========
WrongAnswer
===========

.. image:: https://travis-ci.org/bhuztez/wronganswer.svg?branch=master
    :target: https://travis-ci.org/bhuztez/wronganswer

online judge clients

Quick Start
===========

Clone this repository

.. code-block:: console

    $ git clone git://github.com/bhuztez/wronganswer.git
    $ cd wronganswer

Test solution locally

.. code-block:: console

    $ python3 -m wronganswer test 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' -- echo 'Hello World'

Submit solution to online judge

.. code-block:: console

    $ python3 -m wronganswer submit 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' C solutions/judge.u-aizu.ac.jp/ITP1_1_A.c

Submit solution via vjudge.net

.. code-block:: console

    $ python3 -m wronganswer submit --agent=vjudge.net 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' C solutions/judge.u-aizu.ac.jp/ITP1_1_A.c


Installation
============

Install (Python 3.7 or above is required)

.. code-block:: console

    $ pip3 install --user wronganswer

Now `wa` could be used, instead of `python3 -m wronganswer`. For example, test solution locally

.. code-block:: console

    $ wa test 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' -- echo 'Hello World'


Project
=======

WrongAnswer comes with project support.

Test solution locally

.. code-block:: console

    $ ./c.py test solutions/judge.u-aizu.ac.jp/ITP1_1_A.c

And submit the solution

.. code-block:: console

    $ ./c.py submit solutions/judge.u-aizu.ac.jp/ITP1_1_A.c

Now, take a look at `c.py`__ to see how it works

.. __: ./c.py

First is the boilerplate code

.. code-block:: python3

    #!/usr/bin/env python3

    if __name__ == '__main__':
        from wronganswer.project import main
        main("Wrong Answer Project")
        quit()

Then is the regular expression to extract oj and pid from filename of solution

.. code-block:: python3

    SOLUTION_PATTERN = r'^(?:[^/]+)/(?P<oj>[\w\-.]+)(?:/.*)?/(?P<pid>[A-Za-z0-9_\-]+)\.c$'

Finally, :code:`get_compile_argv` is the function called by WrongAnswer to get command line arguments to call the compiler

.. code-block:: python3

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


Advanced
========

Moreover, WrongAnswer can help you to compile your code locally and submit the assembly to the onlie judge. Run the following to see what is going to be submitted.

.. code-block:: console

    $ ./a.py preview solutions/judge.u-aizu.ac.jp/ITP1_1_A.c



Local judge protocol (experimental)
===================================

For example, You may output :code:`"\x1bXf.3\x1b\\"` just before a floating point number, WrongAnswer would ignore absolute error smaller than :code:`0.001` .


Supported Online Judges
=======================

============== ====== ================ ==========
Online Judge   Submit Fetch test cases vjudge.net
============== ====== ================ ==========
`AOJ`__        Y      Y                Y
`LeetCode`__   Y      N                N
`POJ`__        Y      N                Y
============== ====== ================ ==========

.. __: http://judge.u-aizu.ac.jp/onlinejudge/index.jsp
.. __: https://leetcode.com
.. __: http://poj.org/
