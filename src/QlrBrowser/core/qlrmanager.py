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

from qgis.PyQt.QtCore import pyqtSlot, QCoreApplication, QFile, QIODevice
from qgis.PyQt.QtXml import QDomDocument
from qgis.core import QgsProject, QgsLayerDefinition, QgsLayerTreeGroup, QgsLayerTreeLayer, Qgis, QgsMessageLog, QgsReadWriteContext
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

        # Connect an event when the user clicks "refresh" button
        self.browser.refreshButtonClicked.connect(self.syncCheckedItems)

    def tr(self, message):
        return QCoreApplication.translate('QlrManager', message)

    def log(self, message):
        """ Write to QGIS log from bridge. """
        QgsMessageLog.logMessage(
            '{}'.format(message),
            'QlrBrowser',
             Qgis.Info
        )


    def syncCheckedItems(self):
        """
        Loop through our list and update if layers have been removed
        :return:
        """
        fileitems_to_remove = []
        for fileitem, nodes in self.fileSystemItemToLegendNode.items():
            # print "Checking node", nodehandle
            allRemoved = True
            for nodeinfo in nodes:
                node = self._getlayerTreeNode(nodeinfo)
                if node is not None:
                    allRemoved = False
                    break
            if allRemoved:
                fileitems_to_remove.append(fileitem)
                #self.browser.setPathCheckState(fileitem, False)
                #self.fileSystemItemToLegendNode.pop(fileitem, None)
                
        for fileitem_to_remove in fileitems_to_remove:
            self.browser.setPathCheckState(fileitem_to_remove, False)
            self.fileSystemItemToLegendNode.pop(fileitem_to_remove, None)

    def legend_layersremoved(self, node, indexFrom, indexTo):
        """
        The event that is triggered when a layer is removed.
        """
        # Ignore, if we removed this node
        if self.removingNode:
            #print "We removed this node our self"
            return
        self.syncCheckedItems()

    def browser_itemclicked(self, fileinfo, newState):
        """
        Triggered when an item in the browser is clicked.
        """
        path = fileinfo.fullpath
        if newState == False:
            # Item was unchecked. Remove node(s)
            # if self.fileSystemItemToLegendNode.has_key(path):
            if path in self.fileSystemItemToLegendNode:
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
                message = self.tr(u"Adding qlr-file to the layer panel")
                self.iface.messageBar().pushMessage(self.tr('QlrBrowser'), message, level=Qgis.Info, duration=5)

                # Force show messageBar
                QCoreApplication.processEvents()
                # Load file
                self.load_qlr_file(path)

    def load_qlr_file(self, path):
        try:
        
            # Load qlr into a group owned by us
            group = QgsLayerTreeGroup()
            QgsLayerDefinition.loadLayerDefinition(path, QgsProject.instance(), group) 

            # Get subtree of nodes
            nodes = group.children()
            # plain list of nodes
            nodeslist = []
            # Iterate reversed to maintain original order
            for anode in reversed(nodes):
                # Use clone to get a *copy* of node with no parent 
                addedNode = anode.clone()
                # Create a random (and hopefully unique) ident for node
                internalid = self._random_string()
                nodeinfo = {'internalid': internalid}
                # Set ident as custom property for node
                addedNode.setCustomProperty(QlrManager.customPropertyName, internalid)
                # 
                if isinstance(addedNode, QgsLayerTreeGroup):
                    nodeinfo['type'] = 'group'
                    nodeinfo['name'] = addedNode.name()
                elif isinstance(addedNode, QgsLayerTreeLayer):
                    nodeinfo['type'] = 'layer'
                    nodeinfo['name'] = addedNode.name()
                    nodeinfo['layerid'] = addedNode.layerId()
                nodeslist.append(nodeinfo)
                QgsProject.instance().layerTreeRoot().insertChildNode(0, addedNode)

            self.fileSystemItemToLegendNode[path] = nodeslist
            return True

        except Exception as e:
            self.log('Failed to load qlr at ' + path +': '+ str(e))
            return False
    def _random_string(self):
        return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

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

        self.browser.refreshButtonClicked.disconnect(self.syncCheckedItems)