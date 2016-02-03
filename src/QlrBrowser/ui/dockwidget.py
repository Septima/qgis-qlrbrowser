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
from PyQt4.QtCore import QFileInfo, QDir, pyqtSignal, pyqtSlot, Qt, QTimer
from ..core.filesystemmodel import FileSystemModel

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
        self.filterLineEdit.setPlaceholderText( self.trUtf8(u'Filter'))
        self.treeWidget.setColumnCount(1)
        self.treeWidget.header().hide()

        # Properties
        self.root_paths = set()
        self.file_system = {}
        self.checked_paths = set()

        # Signals
        self.treeWidget.itemDoubleClicked.connect(self._treeitem_doubleclicked)
        self.treeWidget.itemChanged.connect(self._treeitem_changed)
        self.refreshButton.clicked.connect(self.reloadFileSystemInfo)

        # Search
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(500)
        self.timer.timeout.connect( self._fillTree )
        #self.filterLineEdit.textChanged.connect(self._fillTree)
        self.filterLineEdit.textChanged.connect( self.timer.start)

    def addRootPath(self, path):
        self.root_paths.add(path)
        fs = FileSystemModel()
        self.file_system[path] = fs
        fs.updated.connect(self._fillTree)
        fs.setRootPath(path)

    def removeRootPath(self, path):
        self.root_paths.remove(path)
        fs = self.file_system.pop(path, None)
        fs.updated.disconnect(self._fillTree)

    def setPathCheckState(self, path, newState):
        oldState = path in self.checked_paths
        if newState:
            self.checked_paths.add(path)
        elif path in self.checked_paths:
            self.checked_paths.remove(path)
        self._updateTree(path)

    def getIsPathChecked(self, path):
        return path in self.checked_paths

    def getNumCheckedSubPaths(self, path):
        count = sum( (1 for x in self.checked_paths if x.startswith(path)) )
        return count

    def reloadFileSystemInfo(self):
        for fs in self.file_system.values():
            fs.update()

    @pyqtSlot(QtGui.QTreeWidgetItem, int)
    def _treeitem_doubleclicked(self, item, column):
        if item.fileitem.isdir:
            return
        newState = Qt.Checked if item.checkState(column) == Qt.Unchecked else Qt.Unchecked
        item.setCheckState(column, newState)

    @pyqtSlot(QtGui.QTreeWidgetItem, int)
    def _treeitem_changed(self, item, column):
        checked = item.checkState(column) == Qt.Checked
        path = item.fullpath
        self.setPathCheckState(path, checked)
        self.itemStateChanged.emit(item.fileitem, checked)

    def _updateTree(self, filter_path = None):
        # Updates tree display
        # Optionally only the branch which includes filter_path
        iterator = QtGui.QTreeWidgetItemIterator(self.treeWidget)
        item = iterator.value()
        while item:
            # Skip if we only need to update part of tree
            if not filter_path or filter_path.startswith(item.fullpath):
                # checked sub paths
                if item.fileitem.isdir:
                    num = self.getNumCheckedSubPaths(item.fullpath)
                    item.setSubChecked(num)
                # checked
                checked = self.getIsPathChecked(item.fullpath)
                item.setCheckState(0, Qt.Unchecked if not checked else Qt.Checked )
            iterator += 1
            item = iterator.value()

    def _fillTree(self):
        self.treeWidget.clear()

        for basepath in self.root_paths:
            fileitem = self._filteredFileItems(basepath)
            if fileitem:
                baseTreeItem = self._createWidgetItem(fileitem)
                self._fillTreeRecursively(baseTreeItem, fileitem)
                self.treeWidget.addTopLevelItem(baseTreeItem)
                baseTreeItem.setExpanded(True)
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
        checked = self.getIsPathChecked(fileitem.fullpath)
        num_checked_sub_paths = 0
        if fileitem.isdir:
            num_checked_sub_paths = self.getNumCheckedSubPaths(fileitem.fullpath)
        return TreeWidgetItem(fileitem, checked, num_checked_sub_paths)

    #
    # Events
    #
    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

class TreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, fileitem, checked = False, checked_sub_paths = 0):
        super(TreeWidgetItem, self).__init__()
        # Properties for display
        self.fileitem = fileitem
        self.fullpath = fileitem.fullpath
        self.displayname = None
        self.subchecked = checked_sub_paths
        self.setIcon(0, fileitem.icon)
        self.setToolTip(0, self.fullpath)
        self.setCheckState(0, Qt.Unchecked if not checked else Qt.Checked )

        if fileitem.isdir:
            self.setFlags(self.flags() &  ~Qt.ItemIsUserCheckable)
        else:
            self.setFlags(self.flags() | Qt.ItemIsUserCheckable)

        self.updateDisplay()

    def updateDisplay(self):
        name = self.fileitem.displayname
        font = self.font(0)
        font.setBold(False)
        if self.fileitem.isdir:
            if self.subchecked:
                name += ' ({0})'.format(self.subchecked)
                font.setBold(True)
        self.displayname = name
        self.setText(0, name)
        self.setFont(0, font)

    def setSubChecked(self, num):
        self.subchecked = num
        self.updateDisplay()


