import threading

class Lock(object):

  def __init__(self):
    self._thread_locks = {}

  def _key(self, key):
    if isinstance(key, basestring):
      return key
    else:
      return id(key)

  def acquire_lock(self, key):
    try:
      key = self._key(key)
      if key not in self._thread_locks:
        self._thread_locks[key] = threading.Lock()
      self._thread_locks[key].acquire()
      return True
    except:
      print "Unable to acquire the thread lock '%s'" % str(key)
      raise

  def release_lock(self, key):
    key = self._key(key)
    if key in self._thread_locks:
      self._thread_locks[key].release()
      return True
    else:
      return False

  def lock(self, key = None):
    if key:
      key = self._key(key)
    if key in self._thread_locks:
      lock = self._thread_locks[key]
    else:
      lock = threading.Lock()
      if key != None:
        self._thread_locks[key] = lock
    return lock
