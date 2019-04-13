import os
from .zip import ZipFileCacheStore

class UserCacheStore(ZipFileCacheStore):

    def __init__(self):
        super().__init__(os.path.join(os.path.expanduser("~/.cache"), __package__.split(".",1)[0]))
