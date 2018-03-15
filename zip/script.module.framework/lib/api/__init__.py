import os
import sys

try:
    import xbmcaddon
    addon_cfg = xbmcaddon.Addon('script.module.framework')
    __addon_path__ = addon_cfg.getAddonInfo('path')
except:
    __addon_path__ = os.getcwd()
    __addon_path__ = __addon_path__[0:__addon_path__.rfind('/')]


from caching      import Caching
from data         import ZipArchive, Archiving, Hashing, JSON
from lock         import Lock
from storage      import Storage
from parsekit     import PlistKit, JSONKit, RSSKit, YAMLKit, HTTPKit, SOUPKit
from networking   import Networking

try:
    from addonmain    import AddonMain
except:
    pass
