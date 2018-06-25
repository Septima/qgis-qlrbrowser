__author__ = 'asger'

from qgis.PyQt.QtCore import QFileInfo, QDir, pyqtSignal, QObject, QFile, QIODevice, QTextStream
from qgis.PyQt.QtWidgets import QFileIconProvider
from qgis.PyQt.QtXml import QDomDocument
from ..mysettings import Settings
import re

class FileSystemModel(QObject):
    """
    A representation of the file system with <rootpath> as the root.
    """

    updated = pyqtSignal()


    def __init__(self, settings):
        super(FileSystemModel, self).__init__()
        self.rootpath = None
        self.rootitem = None
        self.settings = settings
        self.validSortDelimitChars = ['~','!','#','$','%','&','+','-',';','=','@','^','_']

    def setRootPath(self, path):
        self.rootpath = path.rstrip('/\\')
        # Start filling
        self.update()

    def update(self):
        self.rootitem = FileSystemItem(self.rootpath, True, FileSystemRecursionCounter(self.settings), namingregex=self.namingregex())
        self.updated.emit()

    def namingregex(self):
        if not self.settings.value("useSortDelimitChar"):
            return None
        else:
            char = self.settings.value("sortDelimitChar")
            if char not in self.validSortDelimitChars:
                raise Exception("sortDelimitChar is not valid: '" + char + "'. Should be one of: " + ",".join(self.validSortDelimitChars))
            # Like ^(?:[0-9]{1,3}\~)?(.*)$ for char='~'
            strRex = '^(?:[0-9]{1,3}\\' + char + ')?(.*)$'
            return re.compile(strRex)


class FileSystemItem(QObject):
    """
    An element in the FileSystemModel.
    """
    iconProvider = QFileIconProvider()
    fileExtensions = ['*.qlr']
    xmlSearchableTags = ['title', 'abstract','layername', 'attribution']


    def __init__(self, file, recurse = True, recursion_counter = None, namingregex = None):
        super(FileSystemItem, self).__init__()
        self.namingregex = namingregex

        # Raise exception if root path has too many child elements
        if recursion_counter:
            recursion_counter.increment()

        if isinstance(file, QFileInfo):
            self.fileinfo = file
        else:
            self.fileinfo = QFileInfo(file)
        self.fullpath = self.fileinfo.absoluteFilePath()
        self.basename = self.fileinfo.completeBaseName()
        self.displayname = self.fileinfo.fileName() if self.fileinfo.isDir() else self.fileinfo.completeBaseName()
        if namingregex:
            self.displayname = self.namingregex.match(self.displayname).group(1)
        self.icon = FileSystemItem.iconProvider.icon(self.fileinfo)
        self.isdir = self.fileinfo.isDir()
        self.children = [] if self.isdir else None
        if self.isdir and recurse:
            qdir = QDir(self.fullpath)
            for finfo in qdir.entryInfoList(
                    FileSystemItem.fileExtensions , QDir.Files | QDir.AllDirs | QDir.NoDotAndDotDot,QDir.Name):
                self.children.append(FileSystemItem(finfo, recurse, recursion_counter, self.namingregex))
        else:
            # file
            # Populate this if and when needed
            self.searchablecontent = None

    def filtered(self, filter):
        """
        Filters the root path.
        :filter is a string. Is it contained in the basename or displayname then this item will be rendered.
        :return: the directory item. If nothing is found returns None.
        """
        if not filter:
            return self
        filterlower = filter.lower()
        namematch = self.name_matches(filter)
        if self.isdir:
            if namematch:
                # Stop searching. Return this dir and all sub items
                return FileSystemItem(self.fullpath, True, namingregex = self.namingregex)
            else:
                # Only return dir if at least one sub item is a filter match
                diritem = FileSystemItem(self.fullpath, False, namingregex = self.namingregex)
                for child in self.children:
                    childmatch = child.filtered(filter)
                    if childmatch is not None:
                        diritem.children.append((childmatch))
                if len(diritem.children) > 0:
                    return diritem
        else:
            if self.searchablecontent is None:
                self.searchablecontent = self.get_searchable_content().lower()
            if namematch or self.content_matches(filter):
                return FileSystemItem(self.fullpath, False, namingregex = self.namingregex)
        return None

    def matches(self, searchterm):
        """Returns true if this item mathces the searchterm"""
        return self.name_matches(searchterm) or self.content_matches(searchterm)

    def name_matches(self, searchterm):
        """Returns true if the searchterm matches the name of this item"""
        lowered = searchterm.lower()
        return lowered in self.basename.lower() or lowered in self.displayname.lower()

    def content_matches(self, searchterm):
        """Returns True if the searchterm matches content of this item"""
        if self.isdir:
            return False
        lowered = searchterm.lower()
        if self.searchablecontent is None:
                self.searchablecontent = self.get_searchable_content().lower()
        return lowered in self.searchablecontent

    def get_searchable_content(self):
        """
        Pulls out tags from the object and returns them in order to be used by the filtered() method.
        """
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

class FileSystemRecursionException():
    def __init__(self, message, maxcount):
        self.message = message
        self.maxcount = maxcount

    def __str__(self):
        return repr(self.message)

class FileSystemRecursionCounter():
    def __init__(self, settings):
        self.count = 0
        self.maxcount = settings.value("maxFileSystemObjects")

    def increment(self):
        self.count += 1
        if self.count >= self.maxcount:
            raise FileSystemRecursionException("File system is too big for this file system model", self.maxcount)