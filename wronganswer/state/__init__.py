from abc import ABC, abstractmethod

class StateStore(ABC):

    @abstractmethod
    def load(self, netloc):
        pass

    @abstractmethod
    def store(self, netloc, state):
        pass
