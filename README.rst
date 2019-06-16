===========
WrongAnswer
===========

.. image:: https://travis-ci.org/bhuztez/wronganswer.svg?branch=master
    :target: https://travis-ci.org/bhuztez/wronganswer

online judge clients

Quick Start
===========

Install (Python 3.7 or above is required)

.. code-block:: console

    $ pip3 install --user wronganswer

Clone this repository to get solution used in following examples

.. code-block:: console

    $ git clone git://github.com/bhuztez/wronganswer.git
    $ cd wronganswer

Test solution locally

.. code-block:: console

    $ wa test 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' -- echo 'Hello World'

Submit solution to online judge

.. code-block:: console

    $ wa submit 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' C solutions/judge.u-aizu.ac.jp/ITP1_1_A.c

Submit solution via vjudge.net

.. code-block:: console

    $ wa submit --agent=vjudge.net 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A' C solutions/judge.u-aizu.ac.jp/ITP1_1_A.c


Project
=======

To make life easier, you may put a configuration file in your project, to let WrongAnswer to call the compiler when testing locally.

.. code-block:: console

    $ ./c.py test solutions/judge.u-aizu.ac.jp/ITP1_1_A.c

And to submit the solution

.. code-block:: console

    $ ./c.py submit solutions/judge.u-aizu.ac.jp/ITP1_1_A.c

Moreover, WrongAnswer can help you to compile your code locally and submit the assembly to the onlie judge. Run the following to see what is going to be submitted.

.. code-block:: console

    $ ./c.py preview solutions/judge.u-aizu.ac.jp/ITP1_1_A.c


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
