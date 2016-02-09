__author__ = 'asger'

from PyQt4.QtCore import QFileInfo, QDir, pyqtSignal, QObject, QFile, QIODevice, QTextStream
from PyQt4.QtGui import QFileIconProvider
from PyQt4.QtXml import QDomDocument

class FileSystemModel(QObject):

    updated = pyqtSignal()

    def __init__(self):
        super(FileSystemModel, self).__init__()
        self.rootpath = None
        self.rootitem = None

    def setRootPath(self, path):
        self.rootpath = path.rstrip('/\\')
        # Start filling
        self.update()

    def update(self):
        self.rootitem = FileSystemItem(self.rootpath, True)
        self.updated.emit()

class FileSystemItem(QObject):
    iconProvider = QFileIconProvider()
    fileExtensions = ['*.qlr']
    xmlSearchableTags = ['title', 'abstract','layername', 'attribution']

    def __init__(self, file, recurse = True):
        super(FileSystemItem, self).__init__()

        if isinstance(file, QFileInfo):
            self.fileinfo = file
        else:
            self.fileinfo = QFileInfo(file)
        self.fullpath = self.fileinfo.absoluteFilePath()
        self.basename = self.fileinfo.completeBaseName()
        self.displayname = self.fileinfo.completeBaseName()
        self.icon = FileSystemItem.iconProvider.icon(self.fileinfo)
        self.isdir = self.fileinfo.isDir()
        self.children = [] if self.isdir else None
        if self.isdir and recurse:
            qdir = QDir(self.fullpath)
            for finfo in qdir.entryInfoList( FileSystemItem.fileExtensions , QDir.Files | QDir.AllDirs | QDir.NoDotAndDotDot,QDir.Name):
                self.children.append(FileSystemItem(finfo, recurse))
        else:
            # file
            # Populate this if and when needed
            self.searchablecontent = None

    def filtered(self, filter):
        if not filter:
            return self
        filterlower = filter.lower()
        namematch = filterlower in self.basename.lower() or filterlower in self.displayname.lower()
        if self.isdir:
            if namematch:
                # Stop searching. Return this dir and all sub items
                return FileSystemItem(self.fullpath, True)
            else:
                # Only return dir if at least one sub item is a filter match
                diritem = FileSystemItem(self.fullpath, False)
                for child in self.children:
                    childmatch = child.filtered(filter)
                    if childmatch is not None:
                        diritem.children.append((childmatch))
                if len(diritem.children) > 0:
                    return diritem
        else:
            if self.searchablecontent is None:
                self.searchablecontent = self.get_searchable_content().lower()
            if namematch or filterlower in self.searchablecontent:
                return FileSystemItem(self.fullpath, False)
        return None

    def get_searchable_content(self):
        f = QFile(self.fileinfo.absoluteFilePath())
        f.open(QIODevice.ReadOnly)
        #stream = QTextStream(f)
        #stream.setCodec("UTF-8")
        try:
            doc = QDomDocument()
            doc.setContent( f.readAll() )
            docelt = doc.documentElement()

            texts = []

            for tagName in FileSystemItem.xmlSearchableTags:
                nodes = docelt.elementsByTagName(tagName)
                for i in range(nodes.count()):
                    node = nodes.at(i)
                    value = node.firstChild().toText().data()
                    #print value
                    texts.append( value )

            # Add keywords
            nodes = docelt.elementsByTagName("keywordList")
            for i in range(nodes.count()):
                kwnode = nodes.at(i)
                valnodes = kwnode.toElement().elementsByTagName("value")
                for j in range(valnodes.count()):
                    value = valnodes.at(j).firstChild().toText().data()
                    texts.append(value)

            return u' '.join(texts)
        finally:
            f.close()
