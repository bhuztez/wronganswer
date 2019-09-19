#!/usr/bin/env python3

from setuptools import setup

setup(
    name = 'wronganswer',
    version = '0.1.7',

    url = 'https://github.com/bhuztez/wronganswer',
    description = 'online judge clients',
    license = 'MIT',

    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
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
          'www.lydsy.com = wronganswer.client.BZOJ:BZOJClient',
        ]},
    install_requires = ['html5lib']
)
