# -*- coding: utf-8 -*-

import urlparse
import urllib
import xbmc,xbmcplugin,xbmcgui,xbmcaddon

import sys
import api


# GLOBAL VARS
PLUGIN_ID = 'plugin.video.hieuhien.vn.hdonline'
BASE_URL = 'http://api.hdonline.vn'
CACHE_PATH = xbmc.translatePath("special://temp")

# SETTINGS
settings = xbmcaddon.Addon(id=PLUGIN_ID)

xbmcplugin.setContent(int(sys.argv[1]), 'movies')


action              = None

class main:
	def __init__(self):
		global action
		self.ua = '|User-Agent=iPad'
		params = {}
		splitparams = sys.argv[2][sys.argv[2].find('?') + 1:].split('&')
		for param in splitparams:
			if (len(param) > 0):
				splitparam = param.split('=')
				key = splitparam[0]
				try:    value = splitparam[1].encode("utf-8")
				except: value = splitparam[1]
				params[key] = value

		try:        action = urllib.unquote_plus(params["action"])
		except:     action = None
		try:        resource = urllib.unquote_plus(params["resource"])
		except:     resource = None
		try:        limit = urllib.unquote_plus(params["limit"])
		except:     limit = 20
		try:        offset = urllib.unquote_plus(params["offset"])
		except:     offset = 0
		try:        filmid = urllib.unquote_plus(params["filmid"])
		except:     filmid = 0
		if action == None:                            self.MainMenu()
		if action == 'ListContents':				  self.ListContents(resource, limit, offset)
		if action == 'ListEpisodes':				  self.ListEpisodes(filmid)
		if action == 'Play':						  self.Play(filmid)
		if action == 'ListGenre':				      self.ListGenre(resource)



	def GetProxy(self):
		proxy = None
		http_proxy = settings.getSetting('proxy')
		if http_proxy <> None and http_proxy <> '':
			proxy_username = settings.getSetting('proxy_username')
			proxy_password = settings.getSetting('proxy_password')
			if proxy_username <> None and proxy_username <> '':
				proxy = {'http': 'http://%s:%s@%s' %(urllib.quote(proxy_username), urllib.quote(proxy_password), http_proxy)}
			else:
				proxy = {'http': 'http://' + http_proxy }
		return proxy

	def BuildUrl(self, query):
		return sys.argv[0] + '?' + urllib.urlencode(query)


	def MainMenu(self):
		xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=self.BuildUrl({'action': 'ListContents', 'resource': '/v2/film/list/type/votehome'}), listitem=xbmcgui.ListItem(u'HDO Đề Cử'), isFolder=True)
		xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=self.BuildUrl({'action': 'ListContents', 'resource': '/v2/film/list/type/topmovies'}), listitem=xbmcgui.ListItem(u'Top HDO'), isFolder=True)
		xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=self.BuildUrl({'action': 'ListContents', 'resource': '/v2/film/list/type/cinema'}), listitem=xbmcgui.ListItem(u'Phim Chiếu Rạp'), isFolder=True)
		xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=self.BuildUrl({'action': 'ListContents', 'resource': '/v2/film/list/type/single'}), listitem=xbmcgui.ListItem(u'Phim Lẻ'), isFolder=True)
		xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=self.BuildUrl({'action': 'ListContents', 'resource': '/v2/film/list/type/drama'}), listitem=xbmcgui.ListItem(u'Phim Bộ'), isFolder=True)
		#xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=self.BuildUrl({'action': 'ListGenre', 'resource': '/v2/country'}), listitem=xbmcgui.ListItem(u'Quoc Gia'), isFolder=True)
		#xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=self.BuildUrl({'action': 'ListGenre', 'resource': '/v2/category'}), listitem=xbmcgui.ListItem(u'The Loai'), isFolder=True)
		xbmcplugin.endOfDirectory(int(sys.argv[1]))


	def ListContents(self, resource, limit, offset):
		params = {'limit': limit, 'offset': offset, 'token': self.GetToken()}
		request_url = '%s%s?%s' %(BASE_URL, resource, urllib.urlencode(params))
		result = api.JSONKit(cache_path=CACHE_PATH).ObjectFromURL(request_url, cacheTime=1000*60*30)
		for r in result['result']:
			name = r['name_vn']
			if name == '':
				name = r['name_en']
			name = unicode(name)
			item = xbmcgui.ListItem(name)
			item.setInfo(type="Video", infoLabels={"Label": name, "Title": name, 'Plot': r['info']})
			poster = r['imagelist']['215_311']
			landscape = r['imagelist']['455_215']
			fanart = r['imagelist']['900_500']
			item.setProperty("Fanart_Image", fanart)
			item.setArt({'poster': poster, 'thumb': poster, 'landscape': landscape})
			sequence = r['sequence']
			filmid = r['id']
			u = self.BuildUrl({'action': 'ListEpisodes', 'filmid': filmid})
			xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=int(sequence) == 1)

		if 'total' in result:
			total = int(result['total'])
			if int(offset) < total:
				u = self.BuildUrl({'action': 'ListContents', 'resource': resource, 'offset': int(offset) + int(limit), 'limit': limit})
				item = xbmcgui.ListItem('Xem thêm')
				xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=True)

		xbmcplugin.endOfDirectory(int(sys.argv[1]))
		xbmc.executebuiltin("Container.SetViewMode(57)")


	def ListEpisodes(self, filmid):
		params = {'film': filmid, 'token': self.GetToken()}
		request_url = '%s%s?%s' %(BASE_URL, '/v2/episode', urllib.urlencode(params))
		result = api.JSONKit(cache_path=CACHE_PATH).ObjectFromURL(request_url, cacheTime=1000*60*30)
		result = result['result']
		if len(result) == 1:
			self.Play(result[0]['id'])
		else:
			for r in result:
				name = u''.join([u'Tập', u' ', r['order']])
				poster = r['thumb']
				filmid = r['id']
				item = xbmcgui.ListItem(name)
				item.setInfo(type="Video", infoLabels={"Label": name, "Title": name})
				item.setArt({'poster': poster, 'thumb': poster})
				u = self.BuildUrl({'action': 'Play', 'filmid': filmid})
				xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=False)
			xbmcplugin.endOfDirectory(int(sys.argv[1]))


	def ListGenre(self, resource):
		params = {'film': filmid, 'token': self.GetToken()}
		request_url = '%s%s?%s' %(BASE_URL, '/v2/episode', urllib.urlencode(params))
		result = result = api.JSONKit(cache_path=CACHE_PATH).ObjectFromURL(request_url, cacheTime=1000*60*30)['result']
		if not result['success']:
			xbmcgui.Dialog().notification('Error', result['msg'])
			return
		for r in result:
			item = xbmcgui.ListItem(r['name'])
			u = self.BuildUrl({'action': 'ListContents', 'resource': filmid})
			xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=False)
		xbmcplugin.endOfDirectory(int(sys.argv[1]))


	def Play(self, filmid):
		if filmid == 0:
			return
		params = {'id': filmid, 'token': self.GetToken()}
		request_url = '%s%s?%s' %(BASE_URL, '/v2/episode/play', urllib.urlencode(params))

		link = None
		item = None
		try:
			progress = xbmcgui.DialogProgress()
			progress.create(u'Đăng Tải Phim')
			result = api.JSONKit(cache_path=CACHE_PATH).ObjectFromURL(request_url)
			result = result['result'][0]

			name = unicode(result['film']['name_vn'])
			if int(result['film']['sequence']) == 1:
				name = u''.join([name, u' - ', u'Tập', u' ', result['order']])
			poster = result['thumb']
			link = self.GetLink(result)
			subtitle = []
			for s in result['subtitle']:
				if s['code'] == u'vi':
					subtitle.append(s['link'])

			item = xbmcgui.ListItem(name)
			item.setInfo(type="Video", infoLabels={"Label": name, "Title": name})
			item.setArt({'poster': poster, 'thumb': poster})
			item.setSubtitles(subtitle)

		finally:
			progress.close()
			del progress

		if link == None or item == None:
			xbmcgui.Dialog().notification('Error', u'Link phim có thể bị hỏng.')
		else:
			xbmc.Player().play(link + self.ua, item)


	def GetLink(self, res):
		if 'level' in res and len(res['level']) > 0:
			q = 0
			u = None
			#find level array, get highest res
			for l in res['level']:
				if l['label'] > q:
					q = l['label']
					u = l['file']
			if self.ValidateStream(u):
				return u

		if self.ValidateStream(res['link']):
			return res['link']

		try:
			if self.ValidateStream(res['linkBackup'][0]):
		 		return res['linkBackup'][0]
		except:
			if self.ValidateStream(res['linkbackup'][0]):
		 		return res['linkbackup'][0]
		try:
			if self.ValidateStream(res['fptlink']):
			 	return res['fptlink']
		except:
			pass

		return None


	def GetToken(self):
		request_url = BASE_URL + '/v2/index/gettoken?client=tablet&clientsecret=eba71161466442ff1733fd0c022ac957&device=tablet&platform=ios&version=1.0'
		result = api.JSONKit(cache_path=CACHE_PATH).ObjectFromURL(request_url, cacheTime=1000*60*60)
		return result['result']['token']


	def ValidateStream(self, url):
		if url == None:
			return False
		try:
			import urllib2
			request = urllib2.Request(url)
			request.get_method = lambda : 'HEAD'
			response = urllib2.urlopen(request)
			response.info()
			return True
		except:
			return False

main()
