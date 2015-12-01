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

        # Properties
        self.root_paths = set()
        self.file_system = {}
        self.checked_paths = set()

        # Signals
        self.treeWidget.itemChanged.connect(self._treeitem_changed)

    def addRootPath(self, path):
        self.root_paths.add(path)
        self._updateFileSystemStructure(path)
        self._fillTree()

    def removeRootPath(self, path):
        self.root_paths.remove(path)
        self.file_system.pop(path, None)

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
    def _treeitem_changed(self, item, column):
        checked = item.checkState(column) == Qt.Checked
        path = item.fullpath
        if checked:
            self.checked_paths.add(path)
        else:
            if path in self.checked_paths:
                self.checked_paths.remove(path)
        self.itemStateChanged.emit(item.fileinfo, checked)

    def _fillTree(self):
        self.treeWidget.clear()

        for basepath in self.root_paths:
            fileItem = self._filteredFileItems(basepath)
            baseTreeItem = self._createWidgetItem(fileItem)
            self._fillTreeRecursively(baseTreeItem, fileItem)
            self.treeWidget.addTopLevelItem(baseTreeItem)

    def _filteredFileItems(self, basepath):
        # For now just return unfiltered
        return self.file_system[basepath]['files']

    def _fillTreeRecursively(self, baseWidgetItem, baseFileItem):
        if baseFileItem['type'] == 'qlr':
            return
        for child in baseFileItem['children']:
            childItem = self._createWidgetItem(child)
            if child['type'] == 'dir':
                self._fillTreeRecursively(childItem, child)
            baseWidgetItem.addChild(childItem)

    def _updateFileSystemStructure(self, root_path):
        self.file_system[root_path] = {'files': self._traverseFileSystem(QFileInfo(root_path))}

    def _traverseFileSystem(self, qfileinfo):
        item = { 'fullpath': qfileinfo.absoluteFilePath(),
                 'icon': DockWidget.iconProvider.icon(qfileinfo),
                 'displayname': qfileinfo.baseName()}

        if qfileinfo.isDir():
            qdir = QDir(qfileinfo.absoluteFilePath())
            item['type'] = 'dir'
            item['children'] = []
            for subdirinfo in qdir.entryInfoList(['*.qlr'], QDir.Files | QDir.AllDirs | QDir.NoDotAndDotDot,QDir.Name):
                item['children'].append( self._traverseFileSystem(subdirinfo) )
        else:
            # It is a file
            item['type'] = 'file'
        return item

    def _createWidgetItem(self, fileinfo):
        checked = fileinfo['fullpath'] in self.checked_paths
        return TreeWidgetItem(fileinfo, checked)

    #
    # Events
    #
    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

class TreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, fileinfo, checked = False):
        super(TreeWidgetItem, self).__init__()
        # Properties for display
        self.fileinfo = fileinfo
        self.fullpath = fileinfo['fullpath']
        self.displayname = fileinfo['displayname']
        self.setIcon(0, fileinfo['icon'])
        self.setToolTip(0, self.fullpath)
        self.setText(0, self.displayname)
        self.setCheckState(0, Qt.Unchecked if not checked else Qt.Checked )
        if not fileinfo['type'] == 'dir':
            self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
