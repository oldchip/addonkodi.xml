#!/usr/bin/python
#coding=utf-8
import httplib2, json, re, urllib, os, uuid, contextlib, zipfile
# Tham khảo xbmcswift2 framework cho kodi addon tại
# http://xbmcswift2.readthedocs.io/en/latest/
from xbmcswift2 import Plugin, xbmc, xbmcaddon, xbmcgui
path          = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path') ).decode("utf-8")
cache         = xbmc.translatePath(os.path.join(path,".cache"))
tmp           = xbmc.translatePath('special://temp')
addons_folder = xbmc.translatePath('special://home/addons')

plugin         = Plugin()
addon          = xbmcaddon.Addon("plugin.video.family")
pluginrootpath = "plugin://plugin.video.family"
http           = httplib2.Http(cache, disable_ssl_certificate_validation=True)
query_url      = "https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?gid={gid}&headers=1&tq={tq}"
sheet_headers  = {
	"User-Agent"      : "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.3; WOW64; Trident/7.0)",
	"Accept-Encoding" : "gzip, deflate, sdch, br"
}

def GetSheetIDFromSettings():
	'''
	Hàm lấy url chuyển tiếp
	Parameters
	----------
	url_path : string
		link chứa nội dung m3u playlist
	'''
	sid = "13eYVS7eVDdzMjUeCQeGsQoYajUntmVSq7uCrtOTAxl4"
	resp, content = http.request(plugin.get_setting("GSheetURL"),"HEAD")
	try:
		sid = re.compile("/d/(.+?)/").findall(resp["content-location"])[0]
	except: pass
	return sid

def M3UToItems(url_path=""):
	'''
	Hàm chuyển đổi m3u playlist sang xbmcswift2 items
	Parameters
	----------
	url_path : string
		link chứa nội dung m3u playlist
	'''
	item_re = '\#EXTINF(.*?,)(.*?)\n(.*?)\n'
	(resp, content) = http.request(
		url_path, "GET",
		headers=sheet_headers
	)
	items = []
	matchs = re.compile(item_re).findall(content)
	for info,label,path in matchs:
		thumb = ""
		label2 = ""
		if "tvg-logo" in info:
			thumb = re.compile('tvg-logo=\"?(.*?)\"?,').findall(info)[0]
		if "group-title" in info:
			label2 = re.compile('group-title="(.*?)"').findall(info)[0]
		if label2 != "": label2 = "[%s] " % label2.strip()
		label = "%s%s" % (label2, label.strip())
		item  = {
			"label"      : label,
			"thumbnail"  : thumb.strip(),
			"path"       : path.strip(),
		}
		
		# Nếu là playable link
		if "://" in item["path"]:
			# Kiểu link plugin://
			if item["path"].startswith("plugin://"):
				item["is_playable"] = True
			# Kiểu link .ts
			elif ".ts" in item["path"]: 
				item["path"] = "plugin://plugin.video.f4mTester/?url=%s&streamtype=TSDOWNLOADER&use_proxy_for_chunks=True&name=%s" % (
					urllib.quote(item["path"]),
					urllib.quote_plus(item["label"])
				)
				item["path"] = pluginrootpath + "/executebuiltin/" + urllib.quote_plus(item["path"])
			# Kiểu direct link
			else:
				item["path"] = pluginrootpath + "/play/%s" % urllib.quote_plus(item["path"])
				item["is_playable"] = True
		else:
			# Nếu không phải...
			item["is_playable"] = False

		# Hack xbmcswift2 item to set both is_playable and is_folder to False
		# Required for f4mTester
		if "f4mTester" in item["path"]: item["is_playable"] = False
		items += [item]
	return items

def getItems(url_path="0"):
	'''
	Tạo items theo chuẩn xbmcswift2 từ Google Spreadsheet
	Parameters
	----------
	url_path : string
		Nếu truyền "gid" của Repositories sheet:
			Cài tự động toàn bộ repo trong Repositories sheet
		Nếu truyền link download zip repo
			Download và cài zip repo đó
	tracking_string : string
		 Tên dễ đọc của view
	'''
	# Default VN Open Playlist Sheet ID

	sheet_id = GetSheetIDFromSettings()
	gid     = url_path
	if "@" in url_path:
		gid, sheet_id = url_path.split("@")
	url = query_url.format(
		# Thay sid thành Google Spreadsheet ID của bạn ở đây
		sid = sheet_id,
		tq  = urllib.quote("select A,B,C,D,E"),
		gid = gid
	)
	(resp, content) = http.request(
		url, "GET",
		headers=sheet_headers
	)
	_re = "google.visualization.Query.setResponse\((.+?)\);"
	_json = json.loads(re.compile(_re).findall(content)[0])

	items = []
	for row in _json["table"]["rows"]:
		item = {}
		item["label"]     = getValue(row["c"][0]).encode("utf-8")
		item["label2"]    = getValue(row["c"][4])
		# Nếu phát hiện spreadsheet khác của VNOpenPlaylist
		new_path = getValue(row["c"][1])
		if "@" in url_path and "@" not in new_path and "section/" in new_path:
			gid = re.compile("section/(\d+)").findall(new_path)[0]
			new_path = re.sub(
				'section/\d+',
				'section/%s@%s' % (gid,sheet_id),
				new_path,
				flags=re.IGNORECASE
			)
		item["path"]      = new_path

		item["thumbnail"] = getValue(row["c"][2])
		item["info"]      = {"plot": getValue(row["c"][3])}
		if "plugin://" in item["path"]:
			if "install-repo" in item["path"]:
				item["is_playable"] = False
			elif "/play/" in item["path"]:
				item["is_playable"] = True
		else:			
			# Nếu là playable path thì route đến hàm play_url
			item["is_playable"] = True
			item["path"] = pluginrootpath + "/play/" + urllib.quote_plus(item["path"])
		items += [item]
	return items

def getValue(colid):
	'''
	Hàm lấy giá trị theo cột của của mỗi dòng sheet
	Parameters
	----------
	colid : string
		Số thự tự của cột
	'''
	if colid is not None: return colid["v"]
	else: return ""

@plugin.route('/')
def Home():
	'''	Main Menu
	'''
	GA() # tracking
	Section("0")

@plugin.route('/section/<path>/<tracking_string>')
def Section(path = "0", tracking_string = "Home"):
	'''
	Liệt kê danh sách các item của một sheet
	Parameters
	----------
	path : string
		"gid" của sheet
	tracking_string : string
		 Tên dễ đọc của view
	'''
	GA( # tracking
		"Section - %s" % tracking_string,
		"/section/%s" % path
	)

	items = AddTracking(getItems(path))
	return plugin.finish(items)

@plugin.route('/m3u-section/<path>/<tracking_string>')
def M3USection(path = "0", tracking_string = "M3U"):
	'''
	Liệt kê danh sách các item của sheet M3U Playlist
	Parameters
	----------
	path : string
		"gid" của sheet M3U Playlist
	tracking_string : string
		 Tên dễ đọc của view
	'''
	GA( # tracking
		"M3U Section - %s" % tracking_string,
		"/m3u-section/%s" % path
	)
	items = getItems(path)
	for item in items:
		# Chỉnh lại thành m3u item
		item["path"] = item["path"].replace("/play/","/m3u/")
		if "is_playable" in item:
			del item["is_playable"]
		if "playable" in item:
			del item["playable"]
	return plugin.finish(AddTracking(items))

@plugin.route('/m3u/<path>/<tracking_string>')
def M3U(path = "0", tracking_string = "M3U"):
	'''
	Liệt kê danh sách các item của sheet M3U Playlist
	Parameters
	----------
	path : string
		Link chưa nội dung playlist m3u
	tracking_string : string
		 Tên dễ đọc của view
	'''
	GA( # tracking
		"M3U - %s" % tracking_string,
		"/m3u/%s" % path
	)

	items = M3UToItems(path)
	return plugin.finish(AddTracking(items))

@plugin.route('/install-repo/<path>/<tracking_string>')
def InstallRepo(path = "0", tracking_string = ""):
	'''
	Cài đặt repo
	Parameters
	----------
	path : string
		Nếu truyền "gid" của Repositories sheet:
			Cài tự động toàn bộ repo trong Repositories sheet
		Nếu truyền link download zip repo
			Download và cài zip repo đó
	tracking_string : string
		 Tên dễ đọc của view
	'''
	GA( # tracking
		"Install Repo - %s" % tracking_string,
		"/install-repo/%s" % path
	)
	should_update = False
	if path.isdigit(): # xác định GID
		pDialog = xbmcgui.DialogProgress()
		pDialog.create('Vui lòng đợi','Bắt đầu cài repo','Đang tải...')
		items = getItems(path)
		total = len(items)
		i = 0
		failed = []
		for item in items:
			done = int(100 * i / total)
			pDialog.update(done,'Đang tải', item["label2"] + '...')
			try:
				item["path"] = "http" + item["path"].split("http")[-1]
				download(urllib.unquote_plus(item["path"]), item["label2"])
				should_update = True
			except:
				failed += [item["label"].encode("utf-8")]
			if pDialog.iscanceled():
				break
			i+=1
		pDialog.close()
		if len(failed) > 0:
			dlg = xbmcgui.Dialog()
			s = "Không thể cài các rep sau:\n[COLOR orange]%s[/COLOR]" % "\n".join(failed)
			dlg.ok('Chú ý: Không cài đủ repo!', s)
		else:
			dlg = xbmcgui.Dialog()
			s = "Tất cả repo đã được cài thành công"
			dlg.ok('Cài Repo thành công!', s)

	else: # cài repo riêng lẻ
		try:
			download(path, "")
			should_update = True
			dlg = xbmcgui.Dialog()
			s = "Repo %s đã được cài thành công" % tracking_string
			dlg.ok('Cài Repo thành công!', s)
		except:
			dlg = xbmcgui.Dialog()
			s = "Vùi lòng thử cài lại lần sau"
			dlg.ok('Cài repo thất bại!', s)

	if should_update:
		xbmc.executebuiltin("XBMC.UpdateLocalAddons()")
		xbmc.executebuiltin("XBMC.UpdateAddonRepos()")

@plugin.route('/repo-section/<path>/<tracking_string>')
def RepoSection(path = "0", tracking_string = ""):
	'''
	Liệt kê các repo
	Parameters
	----------
	path : string
		Link download zip repo.
	tracking_string : string
		Tên dễ đọc của view
	'''
	GA( # tracking
		"Repo Section - %s" % tracking_string,
		"/repo-section/%s" % path
	)

	items = getItems(path)
	for item in items:
		if "/play/" in item["path"]:
			item["path"] = item["path"].replace("/play/","/install-repo/")
		# hack xbmcswift2 item to set both is_playable and is_folder to False
		item["is_playable"] = False
	items = AddTracking(items)

	install_all_item = {
		"label"      : "[COLOR green]Tự động cài tất cả Repo dưới (khuyên dùng)[/COLOR]".decode("utf-8"),
		"path"       : pluginrootpath + "/install-repo/%s/%s" % (path,urllib.quote_plus("Install all repo")),
		"is_playable": False,
		"info"       : {"plot": "Bạn nên cài tất cả repo để sử dụng đầy đủ tính năng của [VN Open Playlist]"}
	}
	items = [install_all_item] + items
	return plugin.finish(items)

def download(path,reponame):
	'''
	Parameters
	----------
	path : string
		Link download zip repo.
	reponame : string
		Tên thư mục của repo để kiểm tra đã cài chưa.
		Mặc định được gán cho item["label2"].
		Truyền "" để bỏ qua Kiểm tra đã cài
	'''
	if reponame == "":
		reponame = "temp"
		repo_zip = xbmc.translatePath(os.path.join(tmp,"%s.zip" % reponame))
		urllib.urlretrieve(path,repo_zip)
		with contextlib.closing(zipfile.ZipFile(repo_zip, "r")) as z:
			z.extractall(addons_folder)
	else:
		repo_path = xbmc.translatePath('special://home/addons/%s' % reponame)
		if not os.path.isdir(repo_path):
			if reponame == "": reponame = "temp"
			repo_zip = xbmc.translatePath(os.path.join(tmp,"%s.zip" % reponame))
			urllib.urlretrieve(path,repo_zip)
			with contextlib.closing(zipfile.ZipFile(repo_zip, "r")) as z:
				z.extractall(addons_folder)

def AddTracking(items):
	'''
	Hàm thêm chuỗi tracking cho các item
	Parameters
	----------
	items : list
		Danh sách các item theo chuẩn xbmcswift2.
	'''
	for item in items:
		if "plugin.video.family" in item["path"]:
			item["path"] = "%s/%s" % (item["path"], urllib.quote_plus(item["label"]))
	return items

@plugin.route('/executebuiltin/<path>/<tracking_string>')
def execbuiltin(path,tracking_string=""):
	GA( # tracking
		"Execute Builtin - %s" % tracking_string,
		"/repo-execbuiltin/%s" % path
	)
	xbmc.executebuiltin('XBMC.RunPlugin(%s)' % urllib.unquote_plus(path))

@plugin.route('/play/<url>/<title>')
def play_url(url, title=""):
	GA("Play [%s]" % title, "/play/%s/%s" % (title,url))
	plugin.set_resolved_url(get_playable_url(url))

def get_playable_url(url):
	if "youtube" in url:
		match = re.compile('(youtu\.be\/|youtube-nocookie\.com\/|youtube\.com\/(watch\?(.*&)?v=|(embed|v|user)\/))([^\?&"\'>]+)').findall(url)
		yid   = match[0][len(match[0])-1].replace('v/','')
		url = 'plugin://plugin.video.youtube/play/?video_id=%s' % yid
	else:
		if "://" not in url: url = None
	return url

def GA(title="Home",page="/"):
	'''
	Hàm thống kê lượt sử dụng bằng Google Analytics (GA)
	Parameters
	----------
	title : string
		Tên dễ đọc của view.
	page : string
		Đường dẫn của view.
	'''
	try:
		ga_url    = "http://www.google-analytics.com/collect"
		client_id = open(cid_path).read()
		data      = {
			'v'   : '1',
			'tid' : 'UA-52209804-5', #Thay GA id của bạn ở đây
			'cid' : client_id,
			't'   : 'pageview',
			'dp'  : "VNPlaylist%s" % page,
			'dt'  : "[VNPlaylist] - %s" % title
		}
		http.request(
			ga_url, "POST",
			body=urllib.urlencode(data)
		)
	except:
		pass

# Tạo client id cho GA tracking
# Tham khảo client id tại https://support.google.com/analytics/answer/6205850?hl=vi
device_path = xbmc.translatePath('special://userdata')
if os.path.exists(device_path)==False:
	os.mkdir(device_path)
cid_path = os.path.join(device_path, 'cid')
if os.path.exists(cid_path)==False:
	with open(cid_path,"w") as f:
		f.write(str(uuid.uuid1()))

if __name__ == '__main__':
	plugin.run()
