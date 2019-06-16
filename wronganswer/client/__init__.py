from abc import ABC, abstractmethod
from collections import namedtuple
import csv
from io import StringIO

Env = namedtuple('Env', ['code','name','ver','os','arch','lang','lang_ver'])


class Client(ABC):

    @abstractmethod
    def pid(self, o):
        pass


class Judge(Client):

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.envs = [
            Env._make(v)
            for v in csv.reader(StringIO(cls.__annotations__['ENV'].strip()))
        ]

    @abstractmethod
    def submit(self, pid, env, code):
        pass

    @abstractmethod
    def status(self, token):
        pass

    def prologue(self, pid):
        return b''


class Testcase(Client):

    @abstractmethod
    def testcases(self, pid, writer):
        pass
