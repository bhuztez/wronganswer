from abc import ABC, abstractmethod

class Agent(ABC):

    @abstractmethod
    def submit(self, oj, pid, env, code):
        pass

    @abstractmethod
    def status(self, oj, token):
        pass
