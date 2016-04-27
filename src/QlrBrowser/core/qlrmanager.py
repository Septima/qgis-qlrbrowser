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

from PyQt4.QtCore import pyqtSlot, QCoreApplication
from qgis.core import QgsProject, QgsLayerDefinition, QgsLayerTreeGroup, QgsLayerTreeLayer
from qgis.gui import QgsMessageBar
import random
import string

class QlrManager():
    """ The Manager for the Qlr widget.
    """
    customPropertyName = "qlrbrowserid"

    def __init__(self, iface, qlrbrowser):
        """
        Instantiate the class and set the layerTreeRoot and connect some events.
        """

        self.iface = iface
        self.browser = qlrbrowser

        self.fileSystemItemToLegendNode = dict()
        self.removingNode = False

        # Connect some events whenever layers are added or deleted
        layerTreeRoot = QgsProject.instance().layerTreeRoot()
        layerTreeRoot.removedChildren.connect(self.legend_layersremoved)

        # Connect an event when user interacts with browser
        self.browser.itemStateChanged.connect(self.browser_itemclicked)

    def syncCheckedItems(self):
        """
        Loop through our list and update if layers have been removed
        :return:
        """
        for fileitem, nodes in self.fileSystemItemToLegendNode.items():
            # print "Checking node", nodehandle
            allRemoved = True
            for nodeinfo in nodes:
                node = self._getlayerTreeNode(nodeinfo)
                if node is not None:
                    allRemoved = False
                    break
            if allRemoved:
                self.browser.setPathCheckState(fileitem, False)
                self.fileSystemItemToLegendNode.pop(fileitem, None)

    def legend_layersremoved(self, node, indexFrom, indexTo):
        """
        The event that is triggered when a layer is removed.
        """
        # Ignore, if we removed this node
        if self.removingNode:
            #print "We removed this node our self"
            return
        self.syncCheckedItems()

    @pyqtSlot(object, int)
    def browser_itemclicked(self, fileinfo, newState):
        """
        Triggered when an item in the browser is clicked.
        """
        path = fileinfo.fullpath
        if newState == False:
            # Item was unchecked. Remove node(s)
            if self.fileSystemItemToLegendNode.has_key(path):
                nodes = self.fileSystemItemToLegendNode[path]
                #print "Remove node", nodehandle
                for nodeinfo in nodes:
                    node = self._getlayerTreeNode(nodeinfo)
                    if node:
                        try:
                            self.removingNode = True
                            node.parent().removeChildNode(node)
                        finally:
                            self.removingNode = False
                self.fileSystemItemToLegendNode.pop(path, None)
        else:
            # Item was checked
            if fileinfo.isdir:
                pass
            else:
                msgWidget = self.iface.messageBar().createMessage(u"Indlæser", fileinfo.displayname)
                msgItem = self.iface.messageBar().pushWidget(msgWidget, QgsMessageBar.INFO, duration=0)
                # Force show messageBar
                QCoreApplication.processEvents()
                # Load file
                self.load_qlr_file(path)
                # Remove message
                self.iface.messageBar().popWidget(msgItem)

    def load_qlr_file(self, path):
        # Load qlr into a group owned by us
        try:
            group = QgsLayerTreeGroup()
            QgsLayerDefinition.loadLayerDefinition(path, group)

            # Get subtree of nodes
            nodes = group.children()
            # plain list of nodes
            nodeslist = []
            for addedNode in nodes:
                internalid = self._random_string()
                nodeinfo = {'internalid': internalid}
                addedNode.setCustomProperty(QlrManager.customPropertyName, internalid)
                if isinstance(addedNode, QgsLayerTreeGroup):
                    nodeinfo['type'] = 'group'
                    nodeinfo['name'] = addedNode.name()
                elif isinstance(addedNode, QgsLayerTreeLayer):
                    nodeinfo['type'] = 'layer'
                    nodeinfo['name'] = addedNode.layerName()
                    nodeinfo['layerid'] = addedNode.layerId()
                nodeslist.append(nodeinfo)
                # Remove from parent node. Otherwise we cant add it to a new parent
                group.takeChild(addedNode)
            self.fileSystemItemToLegendNode[path] = nodeslist

            # Insert them into the main project
            QgsProject.instance().layerTreeRoot().insertChildNodes(0, nodes)
            return True
        except:
            # For now just return silently
            return False

    def _random_string(self):
        return ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])

    def _getgroupNodes(self, root_node):
        """
        Returns a group of layers fot a given rootNode.
        :type rootNode: the root node
        """
        groupnodes = []
        for n in root_node.children():
            #print "Checking node", n
            if isinstance(n, QgsLayerTreeGroup):
                #print n, "is a group node"
                groupnodes.append(n)
                groupnodes += self._getgroupNodes(n)
        #print "all group nodes", groupnodes
        return groupnodes

    def _getlayerTreeNode(self, nodeinfo):
        """
        Returns a TreeNode given its nodeinfo.
        :type nodeinfo: object
        """
        root = QgsProject.instance().layerTreeRoot()
        if nodeinfo['type'] == 'layer':
            node = root.findLayer( nodeinfo['layerid'] )
            return node
        elif nodeinfo['type'] == 'group':
            for n in self._getgroupNodes(root):
                #print "is ", n, "our group node?"
                internalid = n.customProperty(QlrManager.customPropertyName)
                #print "properties", n.customProperties()
                #print "internalid", internalid
                if internalid == nodeinfo['internalid']:
                    return n
            # if we reach here we didnt find the group
            return None
        else:
            raise Exception("Wrong type")

    def unload(self):
        """Unload the children of the TreeNode and disconnect its event.
        """
        layerTreeRoot = QgsProject.instance().layerTreeRoot()
        layerTreeRoot.removedChildren.disconnect(self.legend_layersremoved)

        # Disconnect the event handler of this element when user interacts with browser
        self.browser.itemStateChanged.disconnect(self.browser_itemclicked)