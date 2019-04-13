import os
import zipfile
from tempfile import NamedTemporaryFile
from datetime import datetime
from . import CacheStore


class ArchiveReader:

    def __init__(self, path):
        self.archive = ZipFile(path)

    def __iter__(self):
        for name in self.archive.namelist():
            if name.endswith("/"):
                yield name[:-1]

    def __getitem__(self, name):
        return self.archive.open(name + "/in", 'r'), self.archive.open(name + "/out", 'r')


class ZipFile(zipfile.ZipFile):

    def mkdir(self, name):
        # copied from zipfile.py
        zinfo = zipfile.ZipInfo(name + "/", datetime.utcnow().timetuple()[:6])
        zinfo.external_attr = (0o0777 & 0xFFFF) << 16 | 0x10
        zinfo.file_size = 0
        zinfo.compress_size = 0
        zinfo.CRC = 0

        with self._lock:
            if self._seekable:
                self.fp.seek(self.start_dir)
            zinfo.header_offset = self.fp.tell()  # Start of header bytes
            if zinfo.compress_type == zipfile.ZIP_LZMA:
            # Compressed data includes an end-of-stream (EOS) marker
                zinfo.flag_bits |= 0x02

            self._writecheck(zinfo)
            self._didModify = True

            self.filelist.append(zinfo)
            self.NameToInfo[zinfo.filename] = zinfo
            self.fp.write(zinfo.FileHeader(False))
            self.start_dir = self.fp.tell()


class ArchiveWriter:

    def __init__(self, basedir, path):
        self.path = path
        f = NamedTemporaryFile(dir=basedir)
        self.name = f.name
        self.archive = ZipFile(f, 'w')

    def save(self):
        os.link(self.name, self.path)
        self.archive.close()

    def add(self, name):
        self.archive.mkdir(name)
        yield self.archive.open(name + "/in", "w")
        yield self.archive.open(name + "/out", "w")


class ZipFileCacheStore(CacheStore):

    def __init__(self, basedir):
        self.basedir = basedir

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.basedir)

    def get(self, oj, pid):
        path = os.path.join(self.basedir, "data", oj, pid + ".zip")
        try:
            return ArchiveReader(path)
        except FileNotFoundError:
            pass

    def create(self, oj, pid):
        path = os.path.join(self.basedir, "data", oj, pid + ".zip")
        temp = os.path.join(self.basedir, "temp")
        os.makedirs(temp, exist_ok=True)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return ArchiveWriter(temp, path)
