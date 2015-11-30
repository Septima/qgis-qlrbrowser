# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QlrBrowserDockWidget
                                 A QGIS plugin
 This plugin lets the user browse and open qlr files
                             -------------------
        begin                : 2015-11-26
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Asger Skovbo Petersen, Septima
        email                : asger@septima.dk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
__author__ = 'asger'

from qgissettingmanager import SettingDialog
from qlrbrowser_settings import QlrBrowserSettings
from PyQt4 import QtGui, uic
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qlrbrowser_settingsdialog_base.ui'))

class QlrBrowserSettingsDialog(QtGui.QDialog, FORM_CLASS, SettingDialog):
    def __init__(self, parent = None):
        super(QtGui.QDialog, self).__init__(parent)
        self.setupUi(self)
        self.settings = QlrBrowserSettings()
        SettingDialog.__init__(self, self.settings, setValueOnWidgetUpdate=True)

        self.browseButton.clicked.connect(self.browse)

    def browse(self):
        directory = QtGui.QFileDialog.getExistingDirectory(self, self.trUtf8(u"Base directory"))
        if directory:
            self.baseDirectory.setText(directory)
