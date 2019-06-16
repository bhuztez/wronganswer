#!/usr/bin/env python3

from setuptools import setup

setup(
    name = 'wronganswer',
    version = '0.1.3',

    url = 'https://github.com/bhuztez/wronganswer',
    description = 'online judge clients',
    license = 'MIT',

    classifiers = [
        "Development Status :: 1 - Planning",
        "Environment :: Console",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3 :: Only",
    ],

    author = 'bhuztez',
    author_email = 'bhuztez@gmail.com',

    packages = ['wronganswer', 'wronganswer.agent', 'wronganswer.client', 'wronganswer.cache', 'wronganswer.state'],
    entry_points={
        'console_scripts':
        [ 'wa = wronganswer:main' ],
        'online_judge_agents':
        [ 'localhost = wronganswer.agent.local:LocalAgent',
          'vjudge.net = wronganswer.agent.vjudge:VjudgeAgent',
          'cn.vjudge.net = wronganswer.agent.vjudge:VjudgeAgent',
        ],
        'online_judge_clients':
        [ 'judge.u-aizu.ac.jp = wronganswer.client.AOJ:AOJClient',
          'leetcode.com = wronganswer.client.LC:LeetcodeClient',
          'leetcode-cn.com = wronganswer.client.LC:LeetcodeClient',
          'poj.org = wronganswer.client.POJ:POJClient',
        ]},

    install_requires = ['miasma >= 0.1.3'],
)
