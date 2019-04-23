from abc import ABC, abstractmethod

class Client(ABC):

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
