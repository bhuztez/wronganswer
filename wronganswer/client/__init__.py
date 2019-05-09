from abc import ABC, abstractmethod
from collections import namedtuple
import csv
from io import StringIO

Env = namedtuple('Env', ['code','name','ver','os','arch','lang','lang_ver'])


class Client(ABC):

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.envs = [
            Env._make(v)
            for v in csv.reader(StringIO(cls.__annotations__['ENV'].strip()))
        ]

    @abstractmethod
    async def pid(self, o):
        pass

    @abstractmethod
    async def submit(self, pid, env, code):
        pass

    @abstractmethod
    async def status(self, token):
        pass

    async def prologue(self, pid):
        return b''
