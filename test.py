from unittest import main, TestCase
from subprocess import run

def run_wa(*args):
    return run(('wa', '-v', '--debug') + args, check=True)

def run_c(*args):
    return run(('python', './c.py', '-v', '--debug') + args, check=True)

def run_a(*args):
    return run(('python', './a.py', '-v', '--debug') + args, check=True)

class TestWrongAnswer(TestCase):

    def test_command(self):
        with self.subTest("test"):
            run_wa('test', 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A', '--', 'echo', 'Hello', 'World')
        with self.subTest("submit"):
            with self.subTest("AOJ"):
                run_wa('submit', 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=ITP1_1_A', 'C', 'solutions/judge.u-aizu.ac.jp/ITP1_1_A.c')
            with self.subTest("LC"):
                run_wa('submit', 'https://leetcode.com/problems/powx-n/', 'c', 'examples/leetcode.com/50-powx-n.c')
            with self.subTest("POJ"):
                run_wa('submit', 'http://poj.org/problem?id=1000', '1', 'examples/poj.org/1000.c')
            with self.subTest("BZOJ"):
                run_wa('submit', 'https://www.lydsy.com/JudgeOnline/problem.php?id=1000', '1', 'examples/www.lydsy.com/1000.c')

    def test_project(self):
        with self.subTest("test"):
            run_c("test")
        with self.subTest("submit"):
            with self.subTest("solutions"):
                run_c("submit", "solutions")
            with self.subTest("examples"):
                run_c("submit", "examples")
        with self.subTest("clean"):
            run_c("clean")

    def test_project_advanced(self):
        with self.subTest("test"):
            with self.subTest("debug mode"):
                run_a("test")
            with self.subTest("release mode"):
                run_a("test", "--mode", "release")
        with self.subTest("submit"):
            with self.subTest("solutions"):
                run_a("submit", "solutions")
            with self.subTest("examples"):
                run_a("submit", "examples")
        with self.subTest("clean"):
            run_a("clean")

if __name__ == '__main__':
    main()
