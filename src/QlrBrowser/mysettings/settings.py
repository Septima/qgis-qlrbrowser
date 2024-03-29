# -*- coding: utf-8 -*-
from qgis.PyQt import QtCore
from .qgissettingmanager import *

pluginName = "QlrBrowser"

class Settings(SettingManager):
    settings_updated = QtCore.pyqtSignal()

    def __init__(self):
        SettingManager.__init__(self, pluginName)
        self.add_setting(String('baseDirectory', Scope.Global, ''))
        self.add_setting(String('sortDelimitChar', Scope.Global, '~'))
        self.add_setting(Integer('maxFileSystemObjects', Scope.Global, 5000))
        self.add_setting(Bool('useSortDelimitChar', Scope.Global, True))

    def emit_updated(self):
        self.settings_updated.emit()
