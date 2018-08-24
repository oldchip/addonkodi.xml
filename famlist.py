# -*- coding: utf-8 -*-

import xbmc, xbmcaddon

addon = xbmcaddon.Addon(id='plugin.video.tranhuyhoang.playlist')

Autorun = addon.getSetting('en_dis')

if Autorun == 'true':				
    xbmc.executebuiltin("RunAddon(plugin.video.tranhuyhoang.playlist)")