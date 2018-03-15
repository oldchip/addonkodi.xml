import zipfile
import cStringIO as StringIO
import gzip
import hashlib
import binascii
import json
import simplejson
import api
import sys


# from lxml import etree, html, objectify
# from lxml.html import soupparser
# from bs4 import UnicodeDammit


class ZipArchive(object):
  def __init__(self, data=None):
    self._closed = False
    if data:
      self._io = StringIO.StringIO(str(data))
    else:
      self._io = StringIO.StringIO()
    self._zip = zipfile.ZipFile(self._io, mode='a')

  @property
  def Names(self):
    return self._zip.namelist

  def __iter__(self):
    names = self._zip.namelist()
    return names.__iter__()

  def __getitem__(self, name):
    return self._zip.read(name)

  def __setitem__(self, name, data):
    self._zip.writestr(name, data)

  @property
  def Data(self):
    self._io.seek(0)
    return self._io.read()

  def Close(self):
    if not self._closed:
      self._zip.close()
    self._closed = True

  def Test(self):
    return self._zip.testzip()

  def __str__(self):
    return self.Data

  def __del__(self):
    self.Close()
    self._io.close()


class Archiving:

  zip_archive = ZipArchive

  def gzip_decompress(self, data):
    stream = StringIO.StringIO(data)
    gzipper = gzip.GzipFile(mode='rb', fileobj=stream)
    ret = gzipper.read()
    gzipper.close()
    stream.close()
    del gzipper
    del stream
    return ret

  def gzip_compress(self, data):
    stream = StringIO.StringIO()
    gzipper = gzip.GzipFile(mode='wb', fileobj=stream)
    gzipper.write(data)
    gzipper.close()
    ret = stream.getvalue()
    stream.close()
    del gzipper
    del stream
    return ret


class Hashing:
  def _generateHash(self, data, obj, digest=False):
    obj.update(data)
    if digest:
      return obj.digest()
    else:
      return obj.hexdigest()

  def md5(self, data, digest=False):
    return self._generateHash(data, hashlib.md5(), digest)

  def sha1(self, data, digest=False):
    return self._generateHash(data, hashlib.sha1(), digest)

  def sha224(self, data, digest=False):
    return self._generateHash(data, hashlib.sha224(), digest)

  def sha256(self, data, digest=False):
    return self._generateHash(data, hashlib.sha256(), digest)

  def sha384(self, data, digest=False):
    return self._generateHash(data, hashlib.sha384(), digest)

  def sha512(self, data, digest=False):
    return self._generateHash(data, hashlib.sha512(), digest)

  def crc32(self, data):
    crc = binascii.crc32(data)
    return '%08X' % (crc & 2**32L - 1)


class JSON(object):
  def __init__(self):
    self._lock = api.Lock().lock()

  def from_string(self, jsonstring, encoding=None):
    try:
      self._lock.acquire()
      return simplejson.loads(jsonstring, encoding)
    except simplejson.decoder.JSONDecodeError, e:
      print "Error decoding with simplejson, using json instead - %s" % str(e.args[0])
      return json.loads(jsonstring, encoding=encoding)
    finally:
      self._lock.release()

  def to_string(self, obj):
    try:
      self._lock.acquire()
      return simplejson.dumps(obj)
    except:
      print "Error encoding with simplejson, trying json instead"
      return json.dumps(obj)
    finally:
      self._lock.release()

