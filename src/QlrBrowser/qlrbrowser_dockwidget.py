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

import os

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal, pyqtSlot, QModelIndex, Qt
from qlrfilesystemmodel import QlrFileSystemModel

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qlrbrowser_dockwidget_base.ui'))


class QlrBrowserDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    itemClicked = pyqtSignal(QModelIndex, int)

    def __init__(self, rootPath = None, parent=None):
        """Constructor."""
        super(QlrBrowserDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.fileSystemModel = QlrFileSystemModel()
        self.setRootPath(rootPath)

        self.fileSystemModel.itemToggled.connect(self.filesystemmodel_itemtoggled)
        self.treeView.doubleClicked.connect(self.treeview_doubleclicked)


    #
    # Public methods
    #
    def setRootPath(self, path):
        self.fileSystemModel.setRootPath(path)
        rootIndex = self.fileSystemModel.index(path)
        self.treeView.setModel(self.fileSystemModel)
        self.treeView.setRootIndex(rootIndex)
        # Hide size, kind and modified
        self.treeView.hideColumn(1)
        self.treeView.hideColumn(2)
        self.treeView.hideColumn(3)
        self.treeView.show()

    #
    # Events
    #
    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    @pyqtSlot(QModelIndex, int)
    def filesystemmodel_itemtoggled(self, index, newState):
        indexItem = self.fileSystemModel.index(index.row(), 0, index.parent())
        self.itemClicked.emit(indexItem, newState)

    @pyqtSlot(QModelIndex)
    def treeview_doubleclicked(self, index):
        indexItem = self.fileSystemModel.index(index.row(), 0, index.parent())
        self.fileSystemModel.toggleChecked(indexItem, True)

    def toggleItem(self, index):
        self.fileSystemModel.toggleChecked(index, False)