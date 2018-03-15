# -*- coding: utf-8 -*-
import re
import xbmc
import xbmcgui
import xbmcplugin
import sys
import urllib
import api

class AddonMain:
	def __init__(self, plugin, source):
		self.plugin = plugin
		self.source = source

		params = {}
		splitparams = sys.argv[2][sys.argv[2].find('?') + 1:].split('&')
		for param in splitparams:
			if (len(param) > 0):
				splitparam = param.split('=')
				key = splitparam[0]
				try:    value = splitparam[1].encode("utf-8")
				except: value = splitparam[1]
				params[key] = value

		action = None
		try:        action = urllib.unquote_plus(params["action"])
		except:     action = None
		try:        key = urllib.unquote_plus(params["key"])
		except:     key = None
		try:        path = urllib.unquote_plus(params["path"])
		except:     path = ""
		try:        meta_key = urllib.unquote_plus(params["meta_key"])
		except:     meta_key = ""
		try:        stream_key = urllib.unquote_plus(params["stream_key"])
		except:     stream_key = ""
		try:        page = urllib.unquote_plus(params["page"])
		except:     page = 1

		if action == None:                            self.main_menu()
		elif action == 'sub_menu':                    self.sub_menu(key)
		elif action == 'list_medias':                 self.list_medias(path, int(page))
		elif action == 'list_media_items':            self.list_media_items(path)
		elif action == 'play':                        self.play(meta_key, stream_key)
		elif action == 'search':                      self.search()


	def build_url(self, query):
		return sys.argv[0] + '?' + urllib.urlencode(query)


	def main_menu(self):
		menu = self.source.menu()

		for mi in menu:
			obj = menu[mi]
			if type(obj) is list:
				u = self.build_url({'action': 'sub_menu', 'key': mi.encode('utf-8')})
			else:
				u = self.build_url({'action': 'list_medias', 'path': obj})

			item = xbmcgui.ListItem(mi)
			xbmcplugin.addDirectoryItem(handle=self.plugin, url=u, listitem=item, isFolder=True)

		#search
		xbmcplugin.addDirectoryItem(handle=self.plugin, url=self.build_url({'action': 'search'}), listitem=xbmcgui.ListItem(u'Tìm Kiếm'), isFolder=True)
		xbmcplugin.endOfDirectory(self.plugin)


	def sub_menu(self, key):
		menu = self.source.menu()

		_key = key.decode('utf-8')
		for mi in menu[_key]:
			u = self.build_url({'action': 'list_medias', 'path': mi['href']})
			item = xbmcgui.ListItem(mi['label'])
			xbmcplugin.addDirectoryItem(handle=self.plugin, url=u, listitem=item, isFolder=True)

		xbmcplugin.endOfDirectory(self.plugin)


	def list_medias(self, path, page = 1):
		contents = self.source.contents(path)
		self.__list_medias__(contents, page)


	def list_media_items(self, path):
		contents = self.source.media_items(path)

		### if 1 content
		if len(contents) == 1:
			self.play(path, contents.keys()[0].encode('utf-8'))

		### list all episodes/parts
		elif len(contents) > 1:
			for key in sorted(contents, key=self.sort_eps):
				c = contents[key][0]
				u = self.build_url({'action': 'play', 'meta_key': path, 'stream_key': key.encode('utf-8')})
				item = xbmcgui.ListItem(key)
				item.setArt({'poster': c['poster'], 'thumb': c['poster'], 'fanart': c['banner'], 'landscape': c['banner']})
				xbmcplugin.addDirectoryItem(handle=self.plugin, url=u, listitem=item, isFolder=False)
			xbmcplugin.endOfDirectory(self.plugin)


	def search(self):
		kb = xbmc.Keyboard('', u'Tìm Kiếm')
		kb.doModal()

		result = None
		if kb.isConfirmed():
			result = kb.getText()

		if result <> None:
			contents = self.source.search(result)
			self.__list_medias__(contents)


	def __list_medias__(self, contents, page=1):
		for c in contents['items']:
			u = self.build_url({'action': 'list_media_items', 'path': c['href']})
			item = xbmcgui.ListItem(c['title1'])
			item.setInfo(type="Video", infoLabels={'title': c['title1'], 'originaltitle': c['title2'], 'plot': c['info']})
			item.setArt({'poster': c['poster'], 'thumb': c['poster']})
			xbmcplugin.addDirectoryItem(handle=self.plugin, url=u, listitem=item, isFolder=True)

		next_page = contents['next_page']
		if next_page <> None and next_page <> '':
			item = xbmcgui.ListItem(u'Xem thêm')
			u = self.build_url({'action': 'list_medias', 'path': next_page, 'page': page + 1})
			xbmcplugin.addDirectoryItem(handle=self.plugin, url=u, listitem=item, isFolder=True)
		xbmcplugin.endOfDirectory(self.plugin)
		xbmc.executebuiltin("Container.SetViewMode(57)")


	def play(self, meta_key, stream_key):
		contents = self.source.media_items(meta_key)

		#this is a list of servers
		c = contents[stream_key.decode('utf-8')]
		if len(c) == 1:
			c = c[0]
		else:
			dlg = xbmcgui.Dialog()
			opts = []
			for i in c:
				opts.append(i['server_name'])

			ret = dlg.select('Chọn Server', opts)
			if ret > -1:
				c = c[ret]
			else:
				c = None
			del dlg

		if c <> None:
			progress = xbmcgui.DialogProgress()
			progress.create(u'Đăng Tải Phim')
			try:
				stream_url = self.source.resolve_stream(c['href'])
				#if not self.validate_stream(stream_url):
				#	stream_url = None
			except:
				stream_url = None
			finally:
				progress.close()
				del progress

			if stream_url <> None:
				label = c['title1']
				if c['ep_title'] <> '':
					label = u''.join([label, ' - ', c['ep_title']])
				item = xbmcgui.ListItem(label)
				item.setArt({'poster': c['poster'], 'thumb': c['poster'], 'fanart': c['banner'], 'landscape': c['banner']})
				if 'subtitle' in c:
					item.setSubtitles([c['subtitle']])
				xbmc.Player().play(stream_url, item)
			else:
				xbmcgui.Dialog().notification('Error', u'Link phim có thể bị hỏng.')


	def sort_eps(self, x):
		eps = re.compile('.*?(\d+(?:\.\d+)?).*')
		m = eps.match(x)
		if m:
			return float(m.group(1))
		return x

	def validate_stream(self, url):
		if url == None:
			return False
		try:
			if '|' in url:
				url = url[:url.rindex('|')]
			api.HTTPKit(cache_path=xbmc.translatePath('special://temp')).Request(url, method='HEAD', cacheTime=0, headers={'Referer': self.source.base_url})
			return True
		except:
			return False
