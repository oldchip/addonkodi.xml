
import api
import plistlib
import feedparser
import bs4
from networking import GLOBAL_DEFAULT_TIMEOUT


DEFAULT_MAX_SIZE = 1024 * 1024 * 5

def check_size(data, max_size):
	if max_size == None:
		max_size = DEFAULT_MAX_SIZE

	# Make sure we don't try to parse anything greater than the given maximum size.
	if len(data) > max_size:
		raise Framework.exceptions.APIException("Data of size %d is greater than the maximum size %d" % (len(data), max_size))


class BaseHTTPKit:

	def __init__(self, opener=None, cache_path='caches'):
		self._http_headers = {}
		self._custom_headers = {}
		self._opener = opener
		self._networking = api.Networking(cache_path)
		self.cache_time = 0

	@property
	def _opener(self):
		return self._opener


	@property
	def _custom_headers(self):
		return self._http_headers


	def _add_headers(self, headers={}):
		all_headers = dict(self._custom_headers)
		all_headers.update(headers)
		return all_headers


	def _http_request(self, url, *args, **kwargs):
		req = self._networking.http_request(url, *args, **kwargs)
		return req


class PlistKit(BaseHTTPKit):

	def ObjectFromString(self, string, max_size=None):
		check_size(string, max_size)
		return plistlib.readPlistFromString(string)

	def ObjectFromURL(self, url, values=None, headers={}, proxy=None, cacheTime=None, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0, follow_redirects=True, method=None, max_size=None):
		# Update the cache time
		self.cache_time = cacheTime if values == None else 0

		all_headers = self._add_headers(headers)
		return self.ObjectFromString(self._http_request(
			url = url,
			values = values,
			headers = all_headers,
			proxy = proxy,
			cacheTime = cacheTime,
			encoding = encoding,
			errors = errors,
			timeout = timeout,
			immediate = True,
			sleep = sleep,
			opener = self._opener,
			follow_redirects=follow_redirects,
			method=method,
		).content, max_size=max_size)

	def StringFromObject(self, obj):
		return plistlib.writePlistToString(obj)


class JSONKit(BaseHTTPKit):

	def ObjectFromString(self, string, encoding=None, max_size=None):
		check_size(string, max_size)
		return api.JSON().from_string(string, encoding)

	def ObjectFromURL(self, url, values=None, headers={}, proxy=None, cacheTime=None, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0, follow_redirects=True, method=None, max_size=None):
		# Update the cache time
		self.cache_time = cacheTime if values == None else 0

		all_headers = {'Accept': 'text/*, application/json'}
		all_headers.update(self._add_headers(headers))

		return self.ObjectFromString(self._http_request(
			url = url,
			values = values,
			headers = all_headers,
			proxy = proxy,
			cacheTime = cacheTime,
			encoding = encoding,
			errors = errors,
			timeout = timeout,
			immediate = True,
			sleep = sleep,
			opener = self._opener,
			follow_redirects=follow_redirects,
			method=method,
		).content, encoding, max_size=max_size)

	def StringFromObject(self, obj):
		return api.JSON().to_string(obj)


class RSSKit(BaseHTTPKit):

	def FeedFromString(self, string, max_size=None):
		check_size(string, max_size)
		return feedparser.parse(string)

	def FeedFromURL(self, url, values=None, headers={}, proxy=None, cacheTime=None, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0, follow_redirects=True, method=None, max_size=None):
		# Update the cache time
		self.cache_time = cacheTime if values == None else 0

		all_headers = self._add_headers(headers)
		return self.FeedFromString(self._http_request(
			url = url,
			values = values,
			headers = all_headers,
			proxy = proxy,
			cacheTime = cacheTime,
			encoding = encoding,
			errors = errors,
			timeout = timeout,
			immediate = True,
			sleep = sleep,
			opener = self._opener,
			follow_redirects=follow_redirects,
			method=method,
		).content, max_size=max_size)


class YAMLKit(BaseHTTPKit):

	def ObjectFromString(self, string, max_size=None):
		check_size(string, max_size)
		obj = yaml.load(string)
		return obj

	def ObjectFromURL(self, url, values=None, headers={}, proxy=None, cacheTime=None, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0, follow_redirects=True, method=None, max_size=None):
		# Update the cache time
		self.cache_time = cacheTime if values == None else 0

		all_headers = self._add_headers(headers)
		return self.ObjectFromString(self._http_request(
			url = url,
			values = values,
			headers = all_headers,
			proxy = proxy,
			cacheTime = cacheTime,
			encoding = encoding,
			errors = errors,
			timeout = timeout,
			immediate = True,
			sleep = sleep,
			opener = self._opener,
			follow_redirects=follow_redirects,
			method=method,
		).content, max_size=max_size)


class SOUPKit(BaseHTTPKit):

	def SOUPFromString(self, string, max_size=None):
		check_size(string, max_size)
		return bs4.BeautifulSoup(string)

	def SOUPFromURL(self, url, values=None, headers={}, proxy=None, cacheTime=None, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0, follow_redirects=True, method=None, max_size=None):
		# Update the cache time
		self.cache_time = cacheTime if values == None else 0

		all_headers = self._add_headers(headers)
		return self.SOUPFromString(self._http_request(
			url = url,
			values = values,
			headers = all_headers,
			proxy = proxy,
			cacheTime = cacheTime,
			encoding = encoding,
			errors = errors,
			timeout = timeout,
			immediate = True,
			sleep = sleep,
			opener = self._opener,
			follow_redirects=follow_redirects,
			method=method,
		).content, max_size=max_size)


class HTTPKit(BaseHTTPKit):

	@property
	def CacheTime(self):
		return self.cache_time


	@CacheTime.setter
	def CacheTime(self, value):
		self.cache_time = value


	@property
	def Headers(self):
		return self._http_headers


	def Request(self, url, values=None, headers={}, proxy=None, cacheTime=None, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, immediate=True, sleep=0, data=None, follow_redirects=True, method=None):
		self.cache_time = cacheTime if (values == None and data == None) else 0

		all_headers = self._add_headers(headers)

		return self._http_request(
			url = url,
			values = values,
			headers = all_headers,
			proxy = proxy,
			cacheTime = cacheTime,
			encoding = encoding,
			errors = errors,
			timeout = timeout,
			immediate = immediate,
			sleep=sleep,
			data=data,
			opener=self._opener,
			follow_redirects=follow_redirects,
			method=method
		)


	def CookiesForURL(self, url):
		cookies = self._networking.get_cookies_for_url(url, cookie_jar=None)
		return cookies

	def SetPassword(self, url, username, password, realm=None):
		return self._networking.set_http_password(url, username, password, realm)


	def PreCache(self, url, values=None, headers={}, prox=None, cacheTime=None, encoding=None, errors=None):
		self._create_thread(self._precache, url=url, values=values, headers=headers, proxy=proxy, cacheTime=cacheTime, encoding=encoding, errors=errors)

	def _precache(self, url, values=None, headers={}, proxy=None, cacheTime=None, encoding=None, errors=None):
		self.Request(url=url, values=values, headers=headers, proxy=proxy, cacheTime=cacheTime, encoding=encoding, errors=errors, immediate=True)


	@property
	def Cookies(self):
		return self._networking._cookie_jar


	def ClearCookies(self):
		self._networking.clear_cookies(cookie_jar=self._context.cookie_jar)


	def ClearCache(self):
		self._networking.clear_http_cache()

	def _create_thread(self, f, *args, **kwargs):
		th = threading.Thread(
			None,
			self._start_thread,
			name=f.__name__,
			args=(),
			kwargs=dict(
				f = f,
				args = args,
				kwargs = kwargs
			)
		)
		th.start()
		return th

	def _start_thread(self, f, args, kwargs):
		try:
			f(*args, **kwargs)
		except:
			print "Exception in thread named '%s'" % f.__name__
