===========
WrongAnswer
===========

.. image:: https://dev.azure.com/bhuztez/QU/_apis/build/status/bhuztez.wronganswer?branchName=master
    :target: https://dev.azure.com/bhuztez/QU/_build/latest?definitionId=1&branchName=master

online judge clients

Quick Start
===========

Clone this repository

.. code-block:: console

    $ git clone git://github.com/bhuztez/wronganswer.git
    $ cd wronganswer

Test solution locally

.. code-block:: console

    $ python3 -m wronganswer test 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' \
    > -- echo 'Hello World'

Submit solution to online judge

.. code-block:: console

    $ python3 -m wronganswer submit 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' \
    > C solutions/judge.u-aizu.ac.jp/ITP1_1_A.c

Submit solution via vjudge.net

.. code-block:: console

    $ python3 -m wronganswer submit --agent=vjudge.net \
    > 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' \
    > C solutions/judge.u-aizu.ac.jp/ITP1_1_A.c


Installation
============

Install (Python 3.7 or above is required)

.. code-block:: console

    $ pip3 install --user wronganswer

Now `wa` could be used, instead of `python3 -m wronganswer`. For example, test solution locally

.. code-block:: console

    $ wa test 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' \
    > -- echo 'Hello World'


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

First is the boilerplate code, to inform WrongAnswer that this is a project configuration, and make this a script

.. code-block:: python3

    #!/usr/bin/env python3

    if __name__ == '__main__':
        from wronganswer.project import main
        main("Wrong Answer Project")
        quit()

Then is the regular expression to extract domain name of online judge and problem ID from filename of solution

.. code-block:: python3

    SOLUTION_PATTERN = r'^(?:[^/]+)/(?P<oj>[\w\-.]+)(?:/.*)?/(?P<pid>[A-Za-z0-9_\-]+)\.c$'

or you may define a function :code:`get_solution_info`, which should return a tuple if the file is a solution, and :code:`None` if not. The first element of the tuple should be the domain name of online judge and the second element should be the problem ID.

Finally, :code:`get_compile_argv` is the function called by WrongAnswer to get command line arguments to call the compiler. WrongAnswer would pass the source code of the solution to stdin.

.. code-block:: python3

    def get_compile_argv(filename):
        dest = dest_filename(filename)
        return dest, ['gcc','-Wall','-Wextra','-Werror','-x','c','-o',dest,'-']

For scripts, :code:`get_compile_argv` should return :code:`filename, None`.


Advanced
========

Moreover, WrongAnswer can help you to compile your code locally and submit the assembly to the online judge. Run the following to see what is going to be submitted.

.. code-block:: console

    $ ./a.py preview solutions/judge.u-aizu.ac.jp/ITP1_1_A.c


Local judge protocol (experimental)
===================================

For example, You may output :code:`"\x1bXf.3\x1b\\"` just before a floating point number, WrongAnswer would ignore absolute error smaller than :code:`0.001` .


Supported Online Judges
=======================

============== ====== ================ ========== =========================
Online Judge   Submit Fetch test cases vjudge.net Example
============== ====== ================ ========== =========================
`AOJ`__        Y      Y                Y          `ITP1_1_A: Hello World`__
`BZOJ`__       Y      N                N          `1000 A+B Problem`__
`LeetCode`__   Y      N                N          `50. Pow(x, n)`__
`POJ`__        Y      N                Y          `1000 A+B Problem`__
============== ====== ================ ========== =========================

.. __: http://judge.u-aizu.ac.jp/onlinejudge/index.jsp
.. __: ./solutions/judge.u-aizu.ac.jp/ITP1_1_A.c

.. __: https://www.lydsy.com/JudgeOnline/
.. __: ./examples/www.lydsy.com/1000.c

.. __: https://leetcode.com/
.. __: ./examples/leetcode.com/50-powx-n.c

.. __: http://poj.org/
.. __: ./examples/poj.org/1000.c
