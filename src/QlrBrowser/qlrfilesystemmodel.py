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

# See http://www.qtcentre.org/threads/27253-QFileSystemModel-with-checkboxes

from PyQt4 import QtGui
from PyQt4 import QtCore


class QlrFileSystemModel(QtGui.QFileSystemModel):

    itemToggled = QtCore.pyqtSignal(QtCore.QModelIndex, int)

    def __init__(self):
        super(QlrFileSystemModel, self).__init__()
        # only show qlr file
        self.setNameFilters(["*.qlr"])
        self.setNameFilterDisables(False)
        # Files are read only
        self.setReadOnly(True)

        self.checkedItems = set()

    # override data to return checkstate
    def data(self, index, role):
        # if index.column() == self.columnCount() - 1:
        #     if role == QtCore.Qt.DisplayRole:
        #        return QtCore.QString("YourText")
        #     if role == QtCore.Qt.TextAlignmentRole:
        #        return QtCore.Qt.AlignHCenter

        if role == QtCore.Qt.CheckStateRole:
            return  QtCore.Qt.Checked if QtCore.QPersistentModelIndex(index) in self.checkedItems else QtCore.Qt.Unchecked
        return super(QlrFileSystemModel, self).data(index, role)

    def setData(self, index, value, role=None, emitItemToggled = True):
        if role == QtCore.Qt.CheckStateRole:
            persistentIndex = QtCore.QPersistentModelIndex(index)
            if value == QtCore.Qt.Checked:
                self.checkedItems.add(persistentIndex)
            else:
                self.checkedItems.remove(persistentIndex)
            # Emit crashes with QPersistenModelIndex so create a QModelIndex
            if isinstance(index, QtCore.QPersistentModelIndex):
                index = self.index(index.row(), 0, index.parent())
            self.dataChanged.emit(index, index)
            if emitItemToggled:
                self.itemToggled.emit(index, value)
            return True
        return super(QlrFileSystemModel, self).setData(index, value, role)

    # override flags to let items be checkable
    def flags(self, index):
        if not index.column() == 0:
            return super(QlrFileSystemModel, self).flags(index)
        return super(QlrFileSystemModel, self).flags(index) | QtCore.Qt.ItemIsUserCheckable

    def toggleChecked(self, index, emitItemToggled = False):
        if isinstance(index, QtCore.QPersistentModelIndex):
            index = self.index(index.row(), 0, index.parent())
        currentState = self.data(index, QtCore.Qt.CheckStateRole)
        newState = QtCore.Qt.Checked if currentState == QtCore.Qt.Unchecked else QtCore.Qt.Unchecked
        self.setData(index, newState, QtCore.Qt.CheckStateRole, emitItemToggled)
        return newState
