#!/usr/bin/python
#coding=utf-8
import httplib2
import json
import re
import urllib
import os
import uuid
import contextlib
import zipfile
import random
import base64
import time
import thread
from datetime import datetime
# Tham khảo xbmcswift2 framework cho kodi addon tại
# http://xbmcswift2.readthedocs.io/en/latest/
from kodiswift import Plugin, xbmc, xbmcaddon, xbmcgui, actions
path = xbmc.translatePath(
	xbmcaddon.Addon().getAddonInfo('path')).decode("utf-8")
cache = xbmc.translatePath(os.path.join(path, ".cache"))
tmp = xbmc.translatePath('special://temp')
addons_folder = xbmc.translatePath('special://home/addons')
image = xbmc.translatePath(os.path.join(path, "icon.png"))

plugin = Plugin()
addon = xbmcaddon.Addon("plugin.vide0.alohacinema")
pluginrootpath = "plugin://plugin.vide0.alohacinema"
http = httplib2.Http(cache, disable_ssl_certificate_validation=True)
query_url = "https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?gid={gid}&headers=1&tq={tq}"
sheet_headers = {
	"User-Agent": "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.3; WOW64; Trident/7.0)",
	"Accept-Encoding": "gzip, deflate, sdch"
}


def GetSheetIDFromSettings():
	sid = "1EWMWw6B7tI97SSq1RcOcbjmKWk-yicAgoyPaPzs7up0"
	resp, content = http.request(plugin.get_setting("GSheetURL"), "HEAD")
	try:
		sid = re.compile("/d/(.+?)/").findall(resp["content-location"])[0]
	except:
		pass
	return sid

def driveGoogle(name,url,img,fanart,mode,page,query):#64
	ico = os.path.join(iconpath,'gdrive.png')
	if not os.path.isfile(ico):
		b = xread('http://icons.iconarchive.com/icons/marcus-roberto/google-play/512/Google-Drive-icon.png')
		if b : makerequest(ico,b,'wb')

	def googleEPS(url, pageToken=""):
		from resources.lib.utils import googleDrive
		label, items, cookie = googleDrive(url, pageToken)
		
		if not items:
			label = ""
		
		elif "|Google Spreadsheets" in label and isinstance(items,list):
			for title, href, img_ in items:
				addir_info(namecolor(u2s(title),'cyan'),href,img_,'',mode,1,'eps',True)
				
		elif "|Google Spreadsheets" in label and isinstance(items,dict):
			spreadsheetsID = xsearch('([\w|-]{40,})',url)
			for id, title in items.get("ids",[]):
				title = namecolor(namecolor(label)+' List '+title,'cyan')
				href  = "http://docs.google.com/spreadsheets?id=%s&gid=%s"%(spreadsheetsID,id)
				addir_info(title,href,img,'',mode,1,'eps',True)
		
		elif isinstance(items,list) or (isinstance(items,dict) and items.get("nextPageToken")):
			if isinstance(items,dict) and items.get("nextPageToken"):
				nextPageToken = items.get("nextPageToken")
				items         = items.get("items")
			else : nextPageToken = ""
			
			for item in items:
				if 'apps.folder' in item[2]:
					title = namecolor(u2s(item[1]), 'cyan')
					addir_info(title,item[0],img,'',mode,1,'eps',True)
				else:
					title = namecolor('Google drive ','cyan')+u2s(item[1])
					addir_info(title,item[0],img,'',mode,1,'play')
			
			if nextPageToken:
				title = namecolor("Trang tiếp theo ... %d" % (page+1), "lime")
				addir_info(title,url,img,'',mode,page+1,"eps:%s" % nextPageToken,True)
		
		elif isinstance(items,dict):
			label = title = u2s(items.get("fileName",""))
			if title:
				id  = xsearch('([\w|-]{28,})',url)
				addir_info(namecolor('Google drive ','cyan')+title,id,img,'',mode,1,'play')
		
		else : label = ""
		return label
	
	
	
	if not url or url == "gdrive.vn": 
		title=namecolor("Search trên drive.google.com","lime")
		#addir_info(title,'gdrive.com',ico,'',mode,1,'search',True)
				
		url = myaddon.getSetting("gsheetID")
		if not url or url == "Hãy set ID của bạn":
			mess("Hãy set ID Google Spreadsheets")
		
		else : googleEPS(url)
	
	elif query=="search":make_mySearch('',url,'','',mode,'get')
	elif query=="INP" or url=="gdrive.com":
		if query=="INP":query=make_mySearch('',url,'','','','Input')
		if not query.strip():return
		page=1
		
		href = 'https://www.googleapis.com/customsearch/v1element?'+\
				'key=AIzaSyCVAXiUzRYsML1Pv6RwSG1gunmMikTzQqY&num=20&'+\
				'hl=vi&prettyPrint=false&source=gcsc&gss=.com&cx=009789051051551375973:'+\
				'rw4tz3oypqq&googlehost=www.google.com&callback=google.search.Search.'+\
				'apiary19044&q='+urllib.quote_plus('"%s"'%' '.join(query.split()))+'.mkv'

		try    : j = json.loads(xsearch('(\{.+\})',xread(href)))
		except : j = {}
		
		def detail(l):
			title = l.get('titleNoFormatting','').encode('utf-8')
			href  = l.get('unescapedUrl','').encode('utf-8')
			try    : img = l['richSnippet']['cseImage']['src'].encode('utf-8')
			except : img = ''
			return title,href,img
		
		def dk(i):
			return i.get('titleNoFormatting') and i.get('unescapedUrl')
			
		for title,href,img in [detail(i) for i in j.get('results',{}) if dk(i)]:
			addir_info(title,href,img,'',mode,1,'eps',True)

	elif query == "eps" : return googleEPS(url)
	elif "eps:" in query: return googleEPS(url, query.split(":")[1])

	elif query=='play':
		if myaddon.getSetting("gdrivePlay") == "false":
			from resources.lib.utils import googleDriveLink
			link = googleDriveLink(url)
		
		else:
			href = 'https://drive.google.com/'
			b = xread('%suc?id=%s'%(href,url), data = 'X-Json-Requested=true')
			try:
				j = json.loads(xsearch('(\{.+\})',b))
			except:
				j = {}
			link = j.get("downloadUrl","")
			
			if not link:
				from resources.lib.utils import googleDriveLink
				link = googleDriveLink(url)
		
		xbmcsetResolvedUrl(link)

		class fshare:
	def __init__(self, user, passwd):
		self.key  = fshareKey
		self.user   = user
		self.passwd = passwd
		cookie = xrw('fshare.cookie').split('-')
		
		try:
			self.session_id = cookie[0]
			self.token      = cookie[1]
		except:
			self.session_id = ""
			self.token      = ""
		
		self.hd = {'Cookie' : 'session_id=' + self.session_id}
		self.vip = self.getVIP(self.session_id, True)
	
	
	
		
	def results(self, url, hd = {'User-Agent':'Mozilla/5.0'}, data = None):
		try   :  j = json.loads( xread(url, hd, data) )
		except : j = {}
		return j
	
	
	
	
	def getVIP(self, session_id, refresh=False):
		hd = {'Cookie' : 'session_id=' + session_id}
		userInf = self.results("https://api2.fshare.vn/api/user/get", hd)
        
		if refresh and (not userInf or userInf.get("code", 0) == 201 or not session_id):
			self.login(self.user, self.passwd)
			return self.vip
		
		if userInf.get("account_type", "") == "Bundle":
			vip = 1
		
		elif userInf.get("expire_vip","No") == 'Forever':
			vip = 1
		
		else:
			try:
				vip = int(userInf.get("expire_vip","-1"))
			except:
				vip = -1
			
			if vip > 0: 
				from time import time
				vip = 1 if time() < vip else -1
		
		return  vip >= 0
	
	
	
	
	
	def login(self, user, passwd):
		import requests
		data   = '{"app_key" : "%s", "user_email" : "%s", "password" : "%s"}'
		data   = data % (self.key, user, passwd)
		url = "https://118.69.164.19/api/user/login"
		hd = {"Accept-Encoding": "gzip, deflate, sdch"}
		result = requests.post(url, data, headers=hd, verify=False)
		
		try:
			result = json.loads(result.content)
		except:
			result = {}
		
		
		if result.get("code", 0) == 200:
			self.session_id  = result.get("session_id")
			self.token       = result.get("token")
			self.hd = {'Cookie' : 'session_id=' + self.session_id}
			self.vip = self.getVIP(self.session_id)
			xrw('fshare.cookie', self.session_id + "-" + self.token)
			
			if self.vip:
				mess( "Login thành công")
			else:
				mess( "Acc của bạn hết hạn VIP")
		else:
			mess( "Login không thành công!")
			self.vip = False
		
	
	
	
	
	def getLink(self, url, passwd = ""):
		data   = '{"token" : "%s", "url" : "%s", "password" : "%s"}'
		data   = data % (self.token, url, passwd)
		result = self.results("https://api2.fshare.vn/api/session/download", self.hd, data)
		
		link = ""
		if result.get("location"):
			link = result.get("location")
		
		elif result.get("code", 0) == 123 and not passwd:
			from utils import get_input
			passwd = get_input(u'Hãy nhập: Mật khẩu tập tin')
			if passwd:
				link = self.getLink(url, passwd)
		
		if not link:
			if "không tồn tại" in xread(url):
				mess("Tập tin không tồn tại")
				link = "Failed"
		
		return link
