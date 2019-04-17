from abc import ABC, abstractmethod

class Client(ABC):

    @abstractmethod
    def submit(self, pid, env, code):
        pass

    @abstractmethod
    def status(self, token):
        pass

    async def prologue(self, pid):
        return b''
