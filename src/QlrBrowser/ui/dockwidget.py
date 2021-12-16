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
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import QFileInfo, QDir, pyqtSignal, pyqtSlot, Qt, QTimer
from qgis._gui import QgsMessageBar
from qgis.core import Qgis
from ..core.filesystemmodel import FileSystemModel, FileSystemRecursionException

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dockwidget.ui'))

class DockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """The DockWidget class for the Qlr Panel.
    """
    iconProvider = QtWidgets.QFileIconProvider()

    closingPlugin = pyqtSignal()

    itemStateChanged = pyqtSignal(object, bool)

    refreshButtonClicked = pyqtSignal()

    def __init__(self, settings, iface=None):
        """
        Constructor.
        Sets the parent, sets up the UI and fills the tree.
        """
        parent = None if iface is None else iface.mainWindow()
        super(DockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect

        self.settings = settings
        self.setupUi(self)

        self.iface = iface

        # UI
        self.filterLineEdit.setPlaceholderText( self.tr(u'Filter'))
        self.treeWidget.setColumnCount(1)
        self.treeWidget.header().hide()

        # Properties
        self.root_paths = set()
        self.file_system = {}
        self.checked_paths = set()

        # Signals
        self.treeWidget.itemDoubleClicked.connect(self._treeitem_doubleclicked)
        self.treeWidget.itemChanged.connect(self._treeitem_changed)
        self.refreshButton.clicked.connect(self.refreshClicked)

        # Search
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(500)
        self.timer.timeout.connect( self._setFilter )
        self.filterLineEdit.textChanged.connect( self.timer.start)

        # Default fill
        self._fillTree()

    def addRootPath(self, path):
        """Adds the root path and sets up the File System Model and connects it to the _fillTree method.
        """
        if os.path.exists(path):
            self.root_paths.add(path)
            fs = FileSystemModel(self.settings)

            self.file_system[path] = fs

            fs.updated.connect(self._fillTree)
            fs.setRootPath(path)

            self._fillTree()

    def _setFilter(self):
        for basepath in self.root_paths:
            fs =  self.file_system[basepath]
            fs.filter(self.filterLineEdit.text().strip())
        self._fillTree()

    def removeRootPath(self, path):
        """
        Removes the Root Path and disconnects the fillTree() method.
        """
        self.root_paths.remove(path)
        fs = self.file_system.pop(path, None)
        fs.updated.disconnect(self._fillTree)
        self._fillTree()

    def setPathCheckState(self, path, newState):
        """Sets the check state of a path.
        """
        oldState = path in self.checked_paths
        if newState:
            self.checked_paths.add(path)
        elif path in self.checked_paths:
            self.checked_paths.remove(path)
        self._updateTree(path)

    def getIsPathChecked(self, path):
        """
        Returns true whth the path is checked.
        :param path: string
        """
        return path in self.checked_paths

    def getNumCheckedSubPaths(self, path):
        """
        Returns the number of checked items in all subpaths of this element
        :param path: string
        :return: integer, number of checked paths
        """
        count = sum( (1 for x in self.checked_paths if self.is_child_directory(x, path)))

        return count

    def reloadFileSystemInfo(self):
        """Updates the file system info for each element.
        """
        for fs in self.file_system.values():
            try:
                fs.update()
                self._fillTree()
            except FileSystemRecursionException as e:
                self._setRootPathMessage(
                    self.tr(
                    "Configured1 base path has too many files (> {})".format(
                        self.config.get('max_file_system_objects', 1000))
                    )
                )
    def refreshClicked(self):
        self.reloadFileSystemInfo()
        self.refreshButtonClicked.emit()

    @pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def _treeitem_doubleclicked(self, item, column):
        """
        Triggered on a doubleclick event of a Tree Widget.
        """
        if item.fileitem.isdir:
            return
        newState = Qt.Checked if item.checkState(column) == Qt.Unchecked else Qt.Unchecked
        item.setCheckState(column, newState)

    @pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def _treeitem_changed(self, item, column):
        """
        Triggered on a change event of a Tree Widget.
        """
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
        """
        Updates tree display
        :filter_path , string, Optionally only the branch which includes filter_path
        """
        iterator = QtWidgets.QTreeWidgetItemIterator(self.treeWidget)
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
        """
        Fills the tree with items.
        """
        if len(self.root_paths) < 1:
            self._setRootPathMessage(self.tr("No base directory configured..."))
            return

        self.treeWidget.clear()

        for basepath in self.root_paths:
            fs =  self.file_system[basepath]
            if fs.status == "loading":
                self.filterLineEdit.setShowSpinner(True)
                self.filterLineEdit.setReadOnly(True)
                self._setRootPathMessage(self.tr("Loading ..."))
            elif fs.status == "filtering":
                self.filterLineEdit.setShowSpinner(True)
                self.filterLineEdit.setReadOnly(True)
                self._setRootPathMessage(self.tr("Filtering ..."))
            elif fs.status == "overload":
                self.filterLineEdit.setShowSpinner(False)
                self.filterLineEdit.setReadOnly(False)
                self._setRootPathMessage(self.tr("Configured base path has too many files") + "(> {})".format(self.settings.value('maxFileSystemObjects')))
            elif fs.status == "error":
                self.filterLineEdit.setShowSpinner(False)
                self.filterLineEdit.setReadOnly(False)
                self._setRootPathMessage(self.tr("An error ocurred during update"))
            else:
                self.filterLineEdit.setShowSpinner(False)
                self.filterLineEdit.setReadOnly(False)
                fileitem = fs.currentitem
                if fileitem:
                    baseTreeItem = self._createWidgetItem(fileitem)
                    self._fillTreeRecursively(baseTreeItem, fileitem)
                    self.treeWidget.addTopLevelItem(baseTreeItem)
                    baseTreeItem.setExpanded(True)
                    if self.filterLineEdit.text().strip():
                        self._expandTree()
                else:
                    if self.filterLineEdit.text().strip():
                        self._setRootPathMessage(self.tr("No items meet the search filter"))

    def _expandTree(self):
        """
        Expands the tree.
        """
        iterator = QtWidgets.QTreeWidgetItemIterator(self.treeWidget)
        item = iterator.value()
        while item:
            if item.fileitem.matches(self.filterLineEdit.text().strip()):
                tmpitem = item
                while tmpitem:
                    tmpitem.setExpanded(True)
                    tmpitem = tmpitem.parent()
            else:
                item.setExpanded(False)
            iterator += 1
            item = iterator.value()

    def _filteredFileItems(self, basepath):
        """
        Returns the filtered items of the basepath.
        :basepath: string
        """
        # For now just return unfiltered
        fs =  self.file_system[basepath]
        filterText = self.filterLineEdit.text().strip()
        if filterText:
            return fs.currentitem.filtered(filterText)
        else:
            return fs.currentitem

    def _fillTreeRecursively(self, baseWidgetItem, baseFileItem):
        """
        Fills a baseWidgetItem into the baseFileItem
        """
        if not baseFileItem.isdir:
            return
        for child in baseFileItem.children:
            childTreeItem = self._createWidgetItem(child)
            if child.isdir:
                self._fillTreeRecursively(childTreeItem, child)
            baseWidgetItem.addChild(childTreeItem)

    def _createWidgetItem(self, fileitem):
        """
        Creates a widget item from a file item.
        """
        checked = self.getIsPathChecked(fileitem.fullpath)
        num_checked_sub_paths = 0
        if fileitem.isdir:
            num_checked_sub_paths = self.getNumCheckedSubPaths(fileitem.fullpath)
        return TreeWidgetItem(fileitem, checked, num_checked_sub_paths)

    def _checkFileItemExists(self, path):
        """
        Returns true if a path exists.
        :path string
        :returns boolean
        """
        if os.path.exists(path):
            return True
        else:
            self.iface.messageBar().pushMessage(
                self.tr("Qlr Browser Error"),
                self.tr("The selected path does not exist anymore. The Qlr Browser panel is being updated"),
                level=Qgis.Info,
                duration=5)
            return False

    def _setRootPathMessage(self, message):
        self.treeWidget.clear()
        baseTreeItem = QtWidgets.QTreeWidgetItem([message])
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
        :return: boolean
        """
        parent_dir = os.path.join(os.path.realpath(parent_dir), '')
        child_dir = os.path.realpath(child_dir)
        return os.path.commonprefix([child_dir, parent_dir]) == parent_dir


class TreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """
    An item in the Tree Widget.
    """
    def __init__(self, fileitem, checked = False, checked_sub_paths=0):
        """
        Constructor. Sets the properties for display
        """
        super(TreeWidgetItem, self).__init__()
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
        """
        Updates the display, sets the font, displayname.
        """
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
        """
        Sets a subitem to checked.
        :num: The number of the item.
        """
        self.subchecked = num
        self.updateDisplay()


