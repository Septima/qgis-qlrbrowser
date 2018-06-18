# -*- coding: utf-8 -*-
from qgis.PyQt import QtCore
from .qgissettingmanager import *

pluginName = "QlrBrowser"

class Settings(SettingManager):
    def __init__(self):
        SettingManager.__init__(self, pluginName)
        self.add_setting(String('baseDirectory', Scope.Global, ''))
        self.add_setting(String('sortDelimitChar', Scope.Global, '~'))
        self.add_setting(Integer('maxFileSystemObjects', Scope.Global, 1000))
        self.add_setting(Bool('useSortDelimitChar', Scope.Global, True))
