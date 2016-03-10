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
from qgis._gui import QgsMessageBar
from ..core.filesystemmodel import FileSystemModel, FileSystemRecursionException, MAXFILESYSTEMOBJECTS

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dockwidget.ui'))


class DockWidget(QtGui.QDockWidget, FORM_CLASS):
    iconProvider = QtGui.QFileIconProvider()

    closingPlugin = pyqtSignal()

    itemStateChanged = pyqtSignal(object, bool)

    def __init__(self, iface=None):
        """Constructor."""
        parent = None if iface is None else iface.mainWindow()
        super(DockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.iface = iface

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

        # Default fill
        self._fillTree()

    def addRootPath(self, path):
        if os.path.exists(path):
            self.root_paths.add(path)
            fs = FileSystemModel()
            self.file_system[path] = fs
            fs.updated.connect(self._fillTree)
            try:
                fs.setRootPath(path)
            except FileSystemRecursionException as e:
                self._setRootPathMessage(self.trUtf8("Configured base path has too many files (> {})".format(MAXFILESYSTEMOBJECTS)))

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
        """
        Returns the number of checked items in all subpaths of this element
        :param path:
        :return:
        """
        count = sum( (1 for x in self.checked_paths if self.is_child_directory(x, path)))

        return count

    def reloadFileSystemInfo(self):
        for fs in self.file_system.values():
            try:
                fs.update()
            except FileSystemRecursionException as e:
                self._setRootPathMessage(self.trUtf8("Configured base path has too many files (> {})".format(MAXFILESYSTEMOBJECTS)))


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
        if checked:
            # Dont try to turn on a non-existing qlr
            if not self._checkFileItemExists(path):
                # Path no longer exists. Reload filesystem
                self.reloadFileSystemInfo()
                return
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
        if len(self.root_paths) < 1:
            self._setRootPathMessage(self.trUtf8("No base directory configured..."))

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

    def _checkFileItemExists(self, path):
        if os.path.exists(path):
            return True
        else:
            self.iface.messageBar().pushMessage(
                    self.trUtf8("Qlr Browser Error"),
                    self.trUtf8("The selected path does not exist anymore"),
                    level=QgsMessageBar.CRITICAL)
            return False

    def _setRootPathMessage(self, message):
        self.treeWidget.clear()
        baseTreeItem = QtGui.QTreeWidgetItem([message])
        font = baseTreeItem.font(0)
        font.setItalic(True)
        baseTreeItem.setFont(0, font)
        self.treeWidget.addTopLevelItem(baseTreeItem)

    #
    # Events
    #
    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def is_child_directory(self, child_dir, parent_dir):
        """
        Returns true if child_dir is inside parent_dir.
        :param child_dir
        :param parent_dir
        :return:
        """
        parent_dir = os.path.join(os.path.realpath(parent_dir), '')
        child_dir = os.path.realpath(child_dir)
        return os.path.commonprefix([child_dir, parent_dir]) == parent_dir

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


