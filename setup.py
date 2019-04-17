#!/usr/bin/env python3

from setuptools import setup

setup(
    name = 'wronganswer',
    version = '0.0',

    url = 'https://github.com/bhuztez/wronganswer',
    description = 'online judge clients',
    license = 'BSD',

    classifiers = [
        "Development Status :: 1 - Planning",
        "Environment :: Console",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
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
        ]},

    install_requires = ['miasma'],
    dependency_links=['git+https://github.com/bhuztez/miasma@1e23061633e2d23b3e58ff48cd00dbde1ec830d7#egg=miasma-0.0'],
    zip_safe = False,
)
