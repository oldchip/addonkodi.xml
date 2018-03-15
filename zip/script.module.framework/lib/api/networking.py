import urllib
import cookielib
import socket
import os
import weakref
import select
import random
import time
import sys
import base64
import threading
import data
import utils
import caching
import json

urllib2 = utils.ps_import('urllib2')
httplib = utils.ps_import('httplib')

GLOBAL_DEFAULT_TIMEOUT = 150 #httplib._GLOBAL_DEFAULT_TIMEOUT if sys.platform != 'win32' else socket._GLOBAL_DEFAULT_TIMEOUT

import cStringIO as StringIO
#from OpenSSL import SSL



class RedirectError(Exception):
  def __init__(self, code, headers):
    self.code = code
    self.headers = headers

  @property
  def location(self):
    return self.headers['Location']

class HeaderDictionary(dict):
  def __init__(self, *args, **kwargs):
     dict.__init__(self, *args, **kwargs)
     for key in list(self.keys()):
       value = self[key]
       del self[key]
       self[key] = value

  def __setitem__(self, name, value):
    parts = name.split('-')
    i = 0
    while i < len(parts):
      parts[i] = parts[i][0].upper() + parts[i][1:]
      i += 1
    name = '-'.join(parts)
    dict.__setitem__(self, name, value)


class SSLSocket(object):
  def __init__(self):
    self._sock = socket.socket()
    self._con = SSL.Connection(SSL.Context(SSL.SSLv23_METHOD), self._sock)

  def do_handshake(self):
    while True:
      try:
        self._con.do_handshake()
        break
      except SSL.WantReadError:
        select.select([self._sock], [], [], 1.0)

  def recv(self, count):
    while True:
      try:
        return self._con.recv(count)
      except SSL.WantReadError:
        select.select([self._sock], [], [], 1.0)

  def disconnect(self):
    self._sock.shutdown(socket.SHUT_RDWR)
    self._sock.close()

  def __getattr__(self, name):
    return getattr(self._con, name)


class HTTPHeaderProxy(object):
  def __init__(self, headers):
    if headers:
      self._headers = dict(headers)
    else:
      self._headers = {}

  def __getitem__(self, name):
    return self._headers[name.lower()]

  def __iter__(self):
    return self._headers.__iter__()

  def __repr__(self):
    return repr(self._headers)


class RedirectHandler(urllib2.HTTPRedirectHandler):
  def http_error_301(self, req, fp, code, msg, headers):
    if hasattr(req, 'follow_redirects') and req.follow_redirects == False:
      raise RedirectError(code, headers)
    result = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
    return result

  def http_error_302(self, req, fp, code, msg, headers):
    if hasattr(req, 'follow_redirects') and req.follow_redirects == False:
      raise RedirectError(code, headers)
    result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
    return result

  def http_error_303(self, req, fp, code, msg, headers):
    if hasattr(req, 'follow_redirects') and req.follow_redirects == False:
      raise RedirectError(code, headers)
    result = urllib2.HTTPRedirectHandler.http_error_303(self, req, fp, code, msg, headers)
    return result

  def http_error_307(self, req, fp, code, msg, headers):
    if hasattr(req, 'follow_redirects') and req.follow_redirects == False:
      raise RedirectError(code, headers)
    result = urllib2.HTTPRedirectHandler.http_error_307(self, req, fp, code, msg, headers)
    return result


class Request(urllib2.Request):
  def __init__(self, *args, **kwargs):
    urllib2.Request.__init__(self, *args, **kwargs)
    self.follow_redirects = False


class HTTPRequest(object):
  def __init__(self, networking, url, data, headers, cache, encoding, errors, timeout, immediate, sleep, opener, follow_redirects = True, method = None):
    self._url = url
    self._request_headers = HeaderDictionary(headers)
    self._post_data = data
    self._cache = cache
    self._data = None
    self._headers = None
    self._encoding = encoding
    self._errors = errors
    self._timeout = timeout
    self._opener = opener
    self._sleep = sleep
    self._follow_redirects = follow_redirects
    self._method = method
    self._networking = networking
    if immediate:
      self.load()

  def _content_type_allowed(self, content_type):
    for t in ['html', 'xml', 'json', 'javascript']:
      if t in content_type:
        return True
    return False

  def load(self):
    if not self._data:
      if self._cache != None and self._cache['content'] and not self._cache.expired:
        print "Fetching '%s' from the HTTP cache" %self._url
        self._data = self._cache['content']
        self._headers = HTTPHeaderProxy(self._cache.headers)
        return

      print "Requesting '%s'" %self._url

      f = None
      try:
        req = Request(self._url, self._post_data, self._request_headers)
        req.follow_redirects = self._follow_redirects

        # If a method has been set, override the request's default method.
        if self._method:
          req.get_method = lambda: self._method

        f = self._opener.open(req, timeout=self._timeout)

        if f.headers.get('Content-Encoding') == 'gzip':
          self._data = data.Archiving().gzip_decompress(f.read())
        else:
          self._data = f.read()

        #TODO: Move to scheduled save method when the background worker is finished
        self._networking._save()

        info = f.info()
        self._headers = HTTPHeaderProxy(info.dict)
        del info

        if self._cache != None:
          self._cache['content'] = self._data
          self._cache.headers = self._headers._headers

        if self._sleep > 0:
          time.sleep(self._sleep)

      except urllib2.HTTPError, e:
        # Fetch the response body before closing the socket so exception handlers can access it
        if e.hdrs and e.hdrs.getheader('Content-Encoding') == 'gzip':
          content = data.Archiving().gzip_decompress(e.read())
        else:
          content = e.read()

        e.__dict__['content'] = content

        e.close()
        raise

      finally:
        if f:
          f.fp._sock.recv = None  # Hack to stop us leaking file descriptors on errors.
          f.close()
          del f

  @property
  def headers(self):
    if self._headers:
      return self._headers
    else:
      req = Request(self._url, self._post_data, self._request_headers)
      req.follow_redirects = self._follow_redirects
      req.get_method = lambda: 'HEAD'
      f = self._opener.open(req)
      info = f.info()
      self._headers = HTTPHeaderProxy(info.dict)
      return self._headers

  def __str__(self):
    self.load()
    if self._encoding:
      if self._errors:
        result = str(unicode(self._data, self._encoding, self._errors))
      else:
        result = str(unicode(self._data, self._encoding))
    else:
      result = self._data
    return result

  def __len__(self):
    self.load()
    return len(self._data)

  def __add__(self, other):
    return str(self) + other

  def __radd__(self, other):
    return other + str(self)

  @property
  def content(self):
    return self.__str__()


class Networking:
  def __init__(self, data_path='caches'):
    self.default_headers = {
      'Accept-Encoding': 'gzip',
      'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
    }

    self._cookie_jar = cookielib.LWPCookieJar()
    self._cookie_file_path = "%s/http_cookies.dat" % data_path
    if os.path.isfile(self._cookie_file_path):
      self._cookie_jar.load(self._cookie_file_path)

    self._cache_mgr = caching.Caching(data_path).get_cache_manager()
    self._password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()

    self.cache_time = 0
    self.default_timeout = 150

    #self.ssl_socket = SSLSocket

    # Build a global opener.
    self._opener = self.build_opener()


  def build_opener(self, cookie_jar=None):
    if cookie_jar == None:
      cookie_jar = self._cookie_jar

    opener_args = []

    if cookie_jar != None:
      opener_args.append(urllib2.HTTPCookieProcessor(cookie_jar))

    if self._password_mgr != None:
      opener_args.append(urllib2.HTTPBasicAuthHandler(self._password_mgr))

    opener_args.append(RedirectHandler)
    opener_args.append(urllib2.ProxyHandler)
    return urllib2.build_opener(*opener_args)

  def _save(self, cookie_jar=None):
    if self._global_cookies_enabled and (cookie_jar == None or cookie_jar == self._cookie_jar):
      self._cookie_jar.save(self._cookie_file_path)


  def http_request(self, url, values=None, headers={}, proxy=None, cacheTime=None, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, immediate=False, sleep=0, data=None, opener=None, follow_redirects=True, basic_auth=None, method=None):
    if cacheTime == None: cacheTime = self.cache_time

    # Strip off anchors from the end of URLs if provided, as it upsets certain servers if we send them with the request
    pos = url.rfind('#')
    if pos > 0:
      url = url[:pos]

    # If a value dictionary was provided instead of data for a POST body, urlencode it
    if values and not data:
      data = urllib.urlencode(values)

    # If POST data was provided, don't cache the response
    if data:
      cacheTime = 0
      immediate = True

    # If a custom opener was provided, or the cacheTime is 0, don't save data for this request to the HTTP cache
    url_cache = None
    if opener == None:
      opener = self._opener

    if self._http_caching_enabled:
      if cacheTime > 0:
        cache_mgr = self._cache_mgr

        # Check whether we should trim the HTTP cache
        if cache_mgr.item_count > self._cache_mgr.http_cache_max_items + self._cache_mgr.http_cache_max_items_grace:
          cache_mgr.trim(self._cache_mgr.http_cache_max_size, self._cache_mgr.http_cache_max_items)

        url_cache = cache_mgr[url]
        url_cache.set_expiry_interval(cacheTime)

      else:
        # Delete any cached data we have already
        del self._cache_mgr[url]

    # Create a combined dictionary of all headers
    h = dict(self.default_headers)
    h.update(headers)

    if basic_auth != None:
      h['Authorization'] = self.generate_basic_auth_header(*basic_auth)

    #if proxy != None:
    #  opener.add_handler(urllib2.ProxyHandler(proxy))

    return HTTPRequest(self, url, data, h, url_cache, encoding, errors, timeout, immediate, sleep, opener, follow_redirects, method)


  def set_http_password(self, url, username, password, realm=None, manager=None):
    if _global_http_auth_enabled:
      # Strip http:// from the beginning of the url
      if url[0:7] == "http://":
        url = url[7:]
      if manager == None: manager = self._password_mgr
      manager.add_password(realm, url, username, password)


  def get_cookies_for_url(self, url, cookie_jar):
    if cookie_jar == None: cookie_jar = self._cookie_jar
    request = urllib2.Request(url)
    cookie_jar.add_cookie_header(request)
    if request.unredirected_hdrs.has_key('Cookie'):
      return request.unredirected_hdrs['Cookie']
    return None


  def clear_cookies(self, cookie_jar=None):
    if cookie_jar == None:
      cookie_jar = self._cookie_jar
    if cookie_jar:
      cookie_jar.clear()
      self._storage.remove(self._cookie_file_path)
      self._save(cookie_jar)


  def clear_http_cache(self):
    if self._http_caching_enabled:
      self._cache_mgr.clear()


  @property
  def hostname(self):
    return socket.gethostname()


  @property
  def default_timeout(self):
    return socket.getdefaulttimeout()


  @default_timeout.setter
  def default_timeout(self, timeout):
    return socket.setdefaulttimeout(timeout)


  #TODO: Allow args
  def socket(self):
    return socket.socket()


  @property
  def _global_cookies_enabled(self):
    return True


  @property
  def _http_caching_enabled(self):
    return True

  @property
  def _global_http_auth_enabled(self):
    return True


  def generate_basic_auth_header(self, username, password):
    return "Basic  %s" % base64.b64encode('%s: %s' % (username, password))



