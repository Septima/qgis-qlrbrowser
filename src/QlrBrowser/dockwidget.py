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
from PyQt4.QtCore import QFileInfo, QDir, pyqtSignal, Qt

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dockwidget.ui'))


class DockWidget(QtGui.QDockWidget, FORM_CLASS):
    iconProvider = QtGui.QFileIconProvider()

    closingPlugin = pyqtSignal()

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

    def addRootPath(self, path):
        # Only support one root path for now
        self.root_paths.add(path)
        self.updateFileSystemStructure(path)
        self.fillTree()

    def fillTree(self):
        self.treeWidget.clear()

        for basepath in self.root_paths:
            fileItem = self.filteredFileItems(basepath)
            baseTreeItem = TreeWidgetItem(fileItem)
            self.fillTreeRecursively(baseTreeItem, fileItem)
            self.treeWidget.addTopLevelItem(baseTreeItem)

    def filteredFileItems(self, basepath):
        # For now just return unfiltered
        return self.file_system[basepath]['files']

    def fillTreeRecursively(self, baseWidgetItem, baseFileItem):
        if baseFileItem['type'] == 'qlr':
            return
        for child in baseFileItem['children']:
            childItem = TreeWidgetItem(child)
            if child['type'] == 'dir':
                self.fillTreeRecursively(childItem, child)
            baseWidgetItem.addChild(childItem)

    def updateFileSystemStructure(self, root_path):
        self.file_system[root_path] = {'files': self.traverseFileSystem(QFileInfo(root_path))}

    def traverseFileSystem(self, qfileinfo):
        print "traverseFileSystem ", qfileinfo.absoluteFilePath()

        item = { 'fullpath': qfileinfo.absoluteFilePath(),
                 'icon': DockWidget.iconProvider.icon(qfileinfo),
                 'displayname': qfileinfo.baseName()}

        if qfileinfo.isDir():
            qdir = QDir(qfileinfo.absoluteFilePath())
            item['type'] = 'dir'
            item['children'] = []
            for subdirinfo in qdir.entryInfoList(['*.qlr'], QDir.Files | QDir.AllDirs | QDir.NoDotAndDotDot,QDir.Name):
                item['children'].append( self.traverseFileSystem(subdirinfo) )
        else:
            # It is a file
            item['type'] = 'file'
        return item

    #
    # Events
    #
    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

class TreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, fileinfo):
        super(TreeWidgetItem, self).__init__()
        # Properties for display
        self.fullpath = fileinfo['fullpath']
        self.displayname = fileinfo['displayname']
        self.setIcon(0, fileinfo['icon'])
        self.setToolTip(0, self.fullpath)
        self.setText(0, self.displayname)
        self.setCheckState(0, Qt.Unchecked )
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)

