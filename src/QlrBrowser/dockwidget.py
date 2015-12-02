# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DockWidget
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
from PyQt4.QtCore import QFileInfo, QDir, pyqtSignal, pyqtSlot, Qt
from .core.filesystemmodel import FileSystemModel

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dockwidget.ui'))


class DockWidget(QtGui.QDockWidget, FORM_CLASS):
    iconProvider = QtGui.QFileIconProvider()

    closingPlugin = pyqtSignal()

    itemStateChanged = pyqtSignal(object, bool)

    def __init__(self, parent=None):
        """Constructor."""
        super(DockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # UI
        self.filterLineEdit.setPlaceholderText(u'Filter')

        # Properties
        self.root_paths = set()
        self.file_system = {}
        self.checked_paths = set()

        # Signals
        self.treeWidget.itemDoubleClicked.connect(self._treeitem_doubleclicked)
        self.treeWidget.itemChanged.connect(self._treeitem_changed)
        self.filterLineEdit.textChanged.connect(self._fillTree)

    def addRootPath(self, path):
        self.root_paths.add(path)
        fs = FileSystemModel()
        self.file_system[path] = fs
        fs.updated.connect(self._fillTree)
        fs.setRootPath(path)

    def removeRootPath(self, path):
        self.root_paths.remove(path)
        fs = self.file_system.pop(path, None)
        fs.updated.disconnect(self._fillTree())

    def setPathCheckState(self, path, newState):
        oldState = path in self.checked_paths
        if newState:
            self.checked_paths.add(path)
        elif path in self.checked_paths:
            self.checked_paths.remove(path)
        if not oldState == newState:
            iterator = QtGui.QTreeWidgetItemIterator(self.treeWidget)
            item = iterator.value()
            while item:
                if item.fullpath == path:
                    item.setCheckState(0, Qt.Unchecked if not newState else Qt.Checked )
                iterator += 1
                item = iterator.value()

    @pyqtSlot(QtGui.QTreeWidgetItem, int)
    def _treeitem_doubleclicked(self, item, column):
        newState = Qt.Checked if item.checkState(column) == Qt.Unchecked else Qt.Unchecked
        item.setCheckState(column, newState)

    @pyqtSlot(QtGui.QTreeWidgetItem, int)
    def _treeitem_changed(self, item, column):
        checked = item.checkState(column) == Qt.Checked
        path = item.fullpath
        if checked:
            self.checked_paths.add(path)
        else:
            if path in self.checked_paths:
                self.checked_paths.remove(path)
        self.itemStateChanged.emit(item.fileitem, checked)

    def _fillTree(self):
        self.treeWidget.clear()

        for basepath in self.root_paths:
            fileitem = self._filteredFileItems(basepath)
            if fileitem:
                baseTreeItem = self._createWidgetItem(fileitem)
                self._fillTreeRecursively(baseTreeItem, fileitem)
                self.treeWidget.addTopLevelItem(baseTreeItem)
        if self.filterLineEdit.text().strip():
            self._expandTree()

    def _expandTree(self):
        iterator = QtGui.QTreeWidgetItemIterator(self.treeWidget)
        item = iterator.value()
        while item:
            if item.fileitem.isdir:
                item.setExpanded(True)
            iterator += 1
            item = iterator.value()

    def _filteredFileItems(self, basepath):
        # For now just return unfiltered
        fs =  self.file_system[basepath]
        filterText = self.filterLineEdit.text().strip()
        if filterText:
            return fs.rootitem.filtered(filterText)
        else:
            return fs.rootitem

    def _fillTreeRecursively(self, baseWidgetItem, baseFileItem):
        if not baseFileItem.isdir:
            return
        for child in baseFileItem.children:
            childTreeItem = self._createWidgetItem(child)
            if child.isdir:
                self._fillTreeRecursively(childTreeItem, child)
            baseWidgetItem.addChild(childTreeItem)

    def _createWidgetItem(self, fileitem):
        checked = fileitem.fullpath in self.checked_paths
        return TreeWidgetItem(fileitem, checked)

    #
    # Events
    #
    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

class TreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, fileitem, checked = False):
        super(TreeWidgetItem, self).__init__()
        # Properties for display
        self.fileitem = fileitem
        self.fullpath = fileitem.fullpath
        self.displayname = fileitem.displayname
        self.setIcon(0, fileitem.icon)
        self.setToolTip(0, self.fullpath)
        self.setText(0, self.displayname)
        self.setCheckState(0, Qt.Unchecked if not checked else Qt.Checked )
        if fileitem.isdir:
            pass
        else:
            self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
