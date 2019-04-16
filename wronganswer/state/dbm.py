import os
import dbm
from . import StateStore


class DbmStateStore(StateStore):

    def __init__(self, filename):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.db = dbm.open(filename, 'c')

    def load(self, netloc):
        return self.db.get(netloc, None)

    def store(self, netloc, state):
        self.db[netloc] = state
        if hasattr(self.db, 'sync'):
            self.db.sync()
