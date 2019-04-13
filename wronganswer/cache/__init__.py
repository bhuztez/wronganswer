from abc import ABC, abstractmethod

class CacheStore(ABC):

    @abstractmethod
    def get(self, oj, pid):
        pass

    @abstractmethod
    def create(self, oj, pid):
        pass
