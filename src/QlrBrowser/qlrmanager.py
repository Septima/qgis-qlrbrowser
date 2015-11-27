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

from PyQt4.QtCore import Qt, pyqtSlot, QModelIndex, QPersistentModelIndex
from qgis.core import QgsProject, QgsLayerDefinition, QgsLayerTreeGroup, QgsLayerTreeLayer
import random
import string

class QlrManager():
    customPropertyName = "qlrbrowserid"

    def __init__(self, iface, qlrbrowser):
        self.iface = iface
        self.browser = qlrbrowser

        self.fileSystemItemToLegendNode = dict()
        self.modelIndexBeingAdded = None
        self.removingNode = False

        # Get events whenever layers are added or deleted
        layerTreeRoot = QgsProject.instance().layerTreeRoot()
        layerTreeRoot.addedChildren.connect(self.legend_layersadded)
        layerTreeRoot.removedChildren.connect(self.legend_layersremoved)

        # Get events when user interacts with browser
        self.browser.itemClicked.connect(self.browser_itemclicked)


    # Husk, vi kan hente data ud om et item gennem QModelIndex.data()!!!

    # Kan vi koble QmodelIndex sammen med et(eller flere) lag. Lyt på layerTreeRoot.addedChildren som beskrevet
    # http://www.lutraconsulting.co.uk/blog/2014/07/25/qgis-layer-tree-api-part-2/
    # Husk at bruge QPersistentModelIndex (se qlrfilesystemmodel)


    def syncCheckedItems(self):
        # Loop through our list and update if layers have been removed
        for fileitem, nodehandle in self.fileSystemItemToLegendNode.items():
            # print "Checking node", nodehandle
            node = self._getlayerTreeNode(nodehandle)
            if node is None:
                self.browser.toggleItem(fileitem)
                self.fileSystemItemToLegendNode.pop(fileitem, None)

    def legend_layersremoved(self, node, indexFrom, indexTo):
        #print "REMOVED", node, indexFrom, indexTo
        # Ignore, if we removed this node
        if self.removingNode:
            #print "We removed this node our self"
            return
        self.syncCheckedItems()

    def legend_layersadded(self, node, indexFrom, indexTo):
        #print "WILL ADDXXXX", node, indexFrom, indexTo
        # Are nodes being added by us?
        if self.modelIndexBeingAdded:
            # node is added by us
            if not indexFrom == indexTo:
                raise("Yikes")
            addedNode = node.children()[indexFrom]
            internalid = self._random_string()
            nodehandle = {'internalid': internalid}
            addedNode.setCustomProperty(QlrManager.customPropertyName, internalid)
            if isinstance(addedNode, QgsLayerTreeGroup):
                nodehandle['type'] = 'group'
                nodehandle['name'] = addedNode.name()
            elif isinstance(addedNode, QgsLayerTreeLayer):
                nodehandle['type'] = 'layer'
                nodehandle['name'] = addedNode.layerName()
                nodehandle['layerid'] = addedNode.layerId()
            #print "Adding layer", nodehandle
            self.fileSystemItemToLegendNode[self.modelIndexBeingAdded] = nodehandle
        # print self.fileSystemItemToLegendNode

    @pyqtSlot(QModelIndex, int)
    def browser_itemclicked(self, index, newState):
        indexItem = self.browser.fileSystemModel.index(index.row(), 0, index.parent())
        fileName = self.browser.fileSystemModel.fileName(indexItem)
        filePath = self.browser.fileSystemModel.filePath(indexItem)
        if newState == Qt.Unchecked:
            # Item was unchecked. Remove node
            persistent = QPersistentModelIndex(indexItem)
            if self.fileSystemItemToLegendNode.has_key(persistent):
                nodehandle = self.fileSystemItemToLegendNode[persistent]
                #print "Remove node", nodehandle
                node = self._getlayerTreeNode(nodehandle)
                if node:
                    try:
                        self.removingNode = True
                        node.parent().removeChildNode(node)
                    finally:
                        self.removingNode = False
                    self.fileSystemItemToLegendNode.pop(persistent, None)
        else:
            # Item was checked
            if self.browser.fileSystemModel.isDir(indexItem):
                pass
            else:
                treegroup = QgsProject.instance().layerTreeRoot()
                try:
                    self.modelIndexBeingAdded = QPersistentModelIndex(indexItem)
                    QgsLayerDefinition.loadLayerDefinition(filePath, treegroup)
                finally:
                    self.modelIndexBeingAdded = None

    def _random_string(self):
        return ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])

    def _getgroupNodes(self, rootNode):
        groupnodes = []
        for n in rootNode.children():
            #print "Checking node", n
            if isinstance(n, QgsLayerTreeGroup):
                #print n, "is a group node"
                groupnodes.append(n)
                groupnodes += self._getgroupNodes(n)
        #print "all group nodes", groupnodes
        return groupnodes

    def _getlayerTreeNode(self, nodehandle):
        root = QgsProject.instance().layerTreeRoot()
        if nodehandle['type'] == 'layer':
            node = root.findLayer( nodehandle['layerid'] )
            return node
        elif nodehandle['type'] == 'group':
            for n in self._getgroupNodes(root):
                #print "is ", n, "our group node?"
                internalid = n.customProperty(QlrManager.customPropertyName)
                #print "properties", n.customProperties()
                #print "internalid", internalid
                if internalid == nodehandle['internalid']:
                    return n
            # if we reach here we didnt find the group
            return None
        else:
            raise("Wrong type")


    def unload(self):
        layerTreeRoot = QgsProject.instance().layerTreeRoot()
        layerTreeRoot.addedChildren.disconnect(self.legend_layersadded)
        layerTreeRoot.removedChildren.disconnect(self.legend_layersremoved)

        # Get events when user interacts with browser
        self.browser.itemClicked.disconnect(self.browser_itemclicked)