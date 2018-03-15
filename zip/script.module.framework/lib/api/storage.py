
import os
import sys
import shutil
import tempfile
import utils
import lock

if sys.platform == 'win32':
  import ctypes
  kdll = ctypes.windll.LoadLibrary("kernel32.dll")



class Storage(object):

  def __init__(self, storage_path='storage'):
    self.data_path = os.path.join(storage_path, 'Data')
    self.walk = os.walk
    self.copy = shutil.copy
    self.rename = os.rename
    self.remove = os.remove
    self.utime = os.utime
    self.dir_name = os.path.dirname
    self.last_accessed = os.path.getatime
    self.last_modified = os.path.getmtime
    self.path_sep = os.path.sep
    self.base_name = os.path.basename
    self.abs_path = os.path.abspath
    self.make_temp_dir = tempfile.mkdtemp
    self.change_dir = os.chdir
    self.current_dir = os.getcwd

    self.lock = lock.Lock()
    self._mtimes = {}



  def load(self, filename, binary=True, mtime_key=None):
    filename = os.path.abspath(filename)
    lock_key = '_Storage:' + filename
    self.lock.acquire_lock(lock_key)
    data = None
    try:
      if binary: mode = 'rb'
      else: mode = 'r'
      f = open(filename, mode)
      data = f.read()
      f.close()
      self._update_mtime(filename, mtime_key)
    except:
      print "Exception reading file %s" %filename
      data = None
      raise
    finally:
      self.lock.release_lock(lock_key)
      return data

  def save(self, filename, data, binary=True, mtime_key=None):
    if data == None:
      return

    filename = os.path.abspath(filename)
    lock_key = '_Storage:' + filename
    self.lock.acquire_lock(lock_key)
    tempfile = '%s/._%s' % (os.path.dirname(filename), os.path.basename(filename))
    try:
      if os.path.exists(tempfile):
        os.remove(tempfile)
      if binary: mode = 'wb'
      else: mode = 'w'
      f = open(tempfile, mode)
      f.write(str(data))
      f.close()
      if os.path.exists(filename):
        os.remove(filename)
      os.rename(tempfile, filename)
      self._update_mtime(filename, mtime_key)
    except:
      print "Exception writing to %s" %filename
      if os.path.exists(tempfile):
        os.remove(tempfile)
      raise
    finally:
      self.lock.release_lock(lock_key)

  def _update_mtime(self, path, mtime_key):
    mtime_key_id = id(mtime_key)
    if mtime_key_id not in self._mtimes:
      self._mtimes[mtime_key_id] = {}
    self._mtimes[mtime_key_id][path] = self.last_modified(path)

  def has_changed(self, path, mtime_key):
    if not self.file_exists(path):
      return False

    mtime_key_id = id(mtime_key)
    return mtime_key_id not in self._mtimes or path in self._mtimes[mtime_key_id] and self.last_modified(path) != self._mtimes[mtime_key_id][path]

  def list_dir(self, path):
    return os.listdir(path)

  def join_path(self, *args):
    return os.path.join(*args)

  def file_exists(self, path):
    return os.path.exists(path)

  def dir_exists(self, path):
    return os.path.exists(path) and os.path.isdir(path)

  def link_exists(self, path):
    return os.path.exists(path) and os.path.islink(path)

  def make_dirs(self, path):
    if not os.path.exists(path):
      os.makedirs(path)

  def ensure_dirs(self, path):
    try:
      self.make_dirs(path)
    except:
      if not os.path.exists(path):
        raise

  def remove_tree(self, path):
    if self.dir_exists(path):
      shutil.rmtree(path)

  def copy_tree(self, src, target, symlinks=False):
    if self.dir_exists(src):
      if self.dir_exists(target):
        self.remove_tree(target)
      shutil.copytree(src, target, symlinks)

  def file_size(self, path):
    stat = os.stat(path)
    return stat.st_size

  def symlink(self, src, dst):
    if os.path.exists(dst):
      try: os.unlink(dst)
      except: pass

    try:
      if sys.platform == 'win32':
        is_dir = 1 if os.path.isdir(src) else 0
        full_src = os.path.normpath(os.path.join(os.path.dirname(dst), src))
        res = kdll.CreateHardLinkW(unicode(longpathify(dst)), unicode(longpathify(full_src)), 0)
        if res == 0:
          print "Error creating symbolic link from [%s] to %s]" %(src, dst)
      else:
        os.symlink(src, dst)

    except:
      print "Error creating symbolic link from [%s] to %s]" %(src, dst)
