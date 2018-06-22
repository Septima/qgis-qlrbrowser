# -*- coding: utf-8 -*-
import os
from PyQt5 import QtGui, uic
from PyQt5.QtWidgets import QFileDialog
from qgis.gui import (QgsOptionsPageWidget)
from qgis.PyQt.QtWidgets import QVBoxLayout, QFileDialog
from .qgissettingmanager import *



WIDGET, BASE = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), 'settings_dialog.ui')
)

class ConfigOptionsPage(QgsOptionsPageWidget):

    def __init__(self, parent, settings):
        super(ConfigOptionsPage, self).__init__(parent)
        self.settings = settings
        self.config_widget = ConfigDialog(self.settings)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setMargin(0)
        self.setLayout(layout)
        layout.addWidget(self.config_widget)
        self.setObjectName('qkrBrowserOptions')

    def apply(self):
        self.config_widget.accept_dialog()
        self.settings.emit_updated()

class ConfigDialog(WIDGET, BASE, SettingDialog):
    def __init__(self, settings):
        super(ConfigDialog, self).__init__(None)
        self.setupUi(self)
        SettingDialog.__init__(self, settings)
        self.settings = settings
        self.browseButton.clicked.connect(self.browse)

    def browse(self):
        directory = QFileDialog.getExistingDirectory(self, self.tr(u"Base directory"), self.baseDirectory.text())
        if directory:
            self.baseDirectory.setText(directory)

