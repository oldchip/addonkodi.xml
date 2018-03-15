
from __future__ import with_statement
import os, datetime, weakref
import time
from operator import itemgetter

import simplejson
import utils
import api


class CachedItem(object):
  def __init__(self, name, manager):
    self._name = name
    self._hash = api.Hashing().sha1(name)
    self._manager = weakref.proxy(manager)
    self._attributes = {}
    self._item_sizes = {}
    self._expire = 0
    self._update_times()
    self._saved = True


  def __getattr__(self, name):
    if name[0] != '_' and name in self._attributes:
      self._update_times()
      self._save()
      return self._attributes[name]

  def __setattr__(self, name, value):
    if name[0] != '_':
      self._attributes[name] = value
      self._update_times(modified=True)
      self._save()
    object.__setattr__(self, name, value)

  def _item_path(self, name):
    self._manager._storage.ensure_dirs(os.path.join(self._manager._path, self._hash[0:2]))
    return os.path.join(self._manager._path, self._hash[0:2], self._hash[2:] + '.' + name)

  def __getitem__(self, name):
    self._update_times()
    item_path = self._item_path(name)
    self._save()
    if os.path.exists(item_path):
      fdata = self._manager._storage.load(item_path)
      return fdata
    else:
      return None

  def __setitem__(self, name, data):
    self._update_times(modified=True)
    self._item_sizes[name] = len(data)
    self._manager._storage.save(self._item_path(name), data)
    self._save()

  def _update_times(self, modified=False):
    now = datetime.datetime.now()
    self._accessed = now
    if modified:
      self._modified = now
    self._saved = False

  def _save(self):
    self._manager._notify_updated(self)

  @property
  def modified_at(self): return self._modified

  @property
  def accessed_at(self): return self._accessed

  @property
  def expired(self):
    return self._expire == 0 or self._modified < (datetime.datetime.now() - datetime.timedelta(seconds=self._expire))

  def set_expiry_interval(self, interval): self._expire = interval

  @property
  def _attributes_path(self):
    self._manager._storage.ensure_dirs(os.path.join(self._manager._path, self._hash[0:2]))
    return os.path.join(self._manager._path, self._hash[0:2], self._hash[2:] + '_attributes')


class CacheManager(dict):
  def __init__(self, path, http_cache_max_items = 1024, http_cache_max_items_grace = 100, http_cache_max_size = 52428800):

    self.http_cache_max_items            = http_cache_max_items
    self.http_cache_max_items_grace      = http_cache_max_items_grace
    self.http_cache_max_size             = http_cache_max_size
    self._path = path
    self._makedirs()
    self._lock = api.Lock()
    self._info = {}
    self._values = {}
    self._storage = api.Storage()
    self._hashing = api.Hashing()
    self._values_file_path = os.path.join(path, 'StoredValues')
    if os.path.exists(self._values_file_path):
      try:
        data = self._storage.load(self._values_file_path)
        stored_values = simplejson.loads(data)
        self._values.update(stored_values)
      except:
        pass
    # Load the cache info file
    self._info_path = os.path.join(path, 'CacheInfo')
    if self._storage.file_exists(self._info_path):
      try:
        self._info = api.JSON().from_string(self._storage.load(self._info_path))
        # If the cache version is unset, set it now
        if self._get_value(self._name + '.CacheVersion', 0) < 1:
          self._set_value(self._name + '.CacheVersion', 1)

      except:
        print "Exception loading the cache info file from '%s'" %self._info_path
        self.clear()
    elif len(self._storage.list_dir(self._path)) > 0:
      print "No info file found, trashing the cache folder"
      self.clear()
    else:
      self._set_value(self._name + '.CacheVersion', 1)

  def _validate_files(self, file_list, keys):
    # Convert the list of URLs to hashes
    hashes = [self.__hashing.sha1(key) for key in keys]

    for filename in file_list:
      # Compute the original URL hash from the file path
      name_hash = filename[0].split(self._storage.path_sep)[-1] + filename[1]
      if '.' in name_hash:
        name_hash = name_hash[:name_hash.rfind('.')]
      elif len(name_hash) >= 12:
        name_hash = name_hash[:-11]

      # If the file's URL hash isn't in the list, remove it
      filename_str = self._storage.join_path(*filename)
      if name_hash not in hashes:
        self._storage.remove(filename_str)
      else:
        pass

    self._set_value(self._name + '.CacheVersion', 1)


  @property
  def _name(self):
    return os.path.split(self._path)[-1]

  def _makedirs(self):
    api.utils.makedirs(self._path)

  def _save_info(self, acquire_lock=True):
    if acquire_lock:
      self._lock.lock().acquire()
    try:
      self._storage.save(self._info_path, api.JSON().to_string(self._info))
    finally:
      if acquire_lock:
        try:
          self._lock.lock().release()
        except:
          pass

  def _get(self, name):
    if name in self:
      try:
        ref = dict.__getitem__(self, name)()
        if ref:
          return ref
      except:
        pass

    item = CachedItem(name, self)
    self._load_info(item)
    dict.__setitem__(self, name, weakref.ref(item))
    return item

  def __getitem__(self, name):
    with self._lock.lock():
      return self._get(name)

  def __setitem__(self, name, value):
    raise Exception("Cache manager items can't be set directly.")

  def __delitem__(self, key):
    # Load the item from the cache
    item = self._get(key)

    # Remove all data files stored by the cache item
    for name in item._item_sizes:
      path = item._item_path(name)
      if self._storage.file_exists(path):
        self._storage.remove(path)

    # Remove the attributes file
    if self._storage.file_exists(item._attributes_path):
      self._storage.remove(item._attributes_path)

    del item
    if key in self._info:
      del self._info[key]

  def _load_info(self, item):
    try:
      if self._storage.file_exists(item._attributes_path):
        json = self._storage.load(item._attributes_path)
        dct = api.JSON().from_string(json)
        item._accessed = datetime.datetime.fromtimestamp(dct['accessed_at'])
        item._modified = datetime.datetime.fromtimestamp(dct['modified_at'])
        item._expire = dct['expiry_interval']
        item._attributes = dct['attributes']
        item._item_sizes = dct['item_sizes']
    except:
      item._update_times(True)
      item._expire = 0
      item._attributes = {}

  def _notify_updated(self, item):
    with self._lock.lock():
      accessed_at = int(utils.timestamp_from_datetime(item.accessed_at))
      modified_at = None
      if item.modified_at:
        modified_at = int(utils.timestamp_from_datetime(item.modified_at))
      dct = dict(
        accessed_at = accessed_at,
        modified_at = modified_at,
        expiry_interval = int(item._expire),
        attributes = dict(item._attributes),
        item_sizes = dict(item._item_sizes)
      )
      json = api.JSON().to_string(dct)
      self._storage.save(item._attributes_path, json)
      object.__setattr__(item, 'saved', True)

      # Update the cache info dict
      total_size = 0
      for item_name in item._item_sizes:
        total_size += item._item_sizes[item_name]
      self._info[item._name] = [accessed_at, total_size]
    self._save_info()

  def trim(self, max_size, max_items):
    with self._lock:
      try:
        # Sort the items - the least recently accessed will be first in the list
        info = sorted(self._info.items(), key=itemgetter(1))

        # Remove items if the count is above the maximum limit
        info_len = len(info)
        if info_len > max_items:
          remove_count = info_len - max_items
          for item in info[:remove_count]:
            del self[item[0]]
          info = info[remove_count:]

        # Compute the total size of the cache
        size = 0
        for item in info:
          size += item[1][1]

        # While the size is greater than the maxiumum allowed size, whack the least recently accessed cache item
        while size > max_size:
          key, attrs = info[0]
          item_size = attrs[1]

          del self[key]

          # Decrement the size
          size -= item_size

          del info[0]
          del self._info[key]

        del info

      except:
        pass

    self._save_info()

  def clear(self):
    with self._lock.lock():
      try:
          self._storage.remove_tree(self._path)
      except:
        print 'Exception trashing the cache folder'
      self._makedirs()
      dict.clear(self)
      self._info = {}
      self._set_value(self._name + '.CacheVersion', 1)
      self._save_info(acquire_lock=False)

  @property
  def item_count(self):
    return len(self._info)


  def _set_value(self, key, value):
    self._values[key] = value
    json_str = api.JSON().to_string(self._values)
    self._storage.save(self._values_file_path, json_str)

  def _get_value(self, key, default=None):
    return self._values.get(key, default)

class Caching(object):

  def __init__(self, data_path = 'storage'):
    self.caches_path = data_path
    self.managers = {}

  def get_cache_manager(self, name = 'Caches'):
    if name in self.managers:
      return self.managers[name]

    mgr = CacheManager(os.path.join(self.caches_path, name))
    self.managers[name] = mgr
    return mgr



