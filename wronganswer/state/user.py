import os
from .dbm import DbmStateStore

class UserStateStore(DbmStateStore):

    def __init__(self):
        super().__init__(os.path.join(os.path.expanduser("~/.config"), __package__.split(".",1)[0], "state.dbm"))
