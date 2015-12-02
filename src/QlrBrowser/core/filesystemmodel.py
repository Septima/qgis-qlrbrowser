__author__ = 'asger'

from PyQt4.QtCore import QFileInfo, QDir, pyqtSignal, QObject
from PyQt4.QtGui import QFileIconProvider

class FileSystemModel(QObject):

    updated = pyqtSignal()

    def __init__(self):
        super(FileSystemModel, self).__init__()
        self.rootpath = None
        self.rootitem = None

    def setRootPath(self, path):
        self.rootpath = path
        # Start filling
        self.update()

    def update(self):
        self.rootitem = FileSystemItem(self.rootpath, True)
        self.updated.emit()

class FileSystemItem(QObject):
    iconProvider = QFileIconProvider()

    def __init__(self, file, recurse = True):
        super(FileSystemItem, self).__init__()

        if isinstance(file, QFileInfo):
            self.fileinfo = file
        else:
            self.fileinfo = QFileInfo(file)
        self.fullpath = self.fileinfo.absoluteFilePath()
        self.basename = self.fileinfo.baseName()
        self.displayname = self.fileinfo.baseName()
        self.icon = FileSystemItem.iconProvider.icon(self.fileinfo)
        self.isdir = self.fileinfo.isDir()
        self.children = [] if self.isdir else None
        if self.isdir and recurse:
            qdir = QDir(self.fullpath)
            for finfo in qdir.entryInfoList(['*.qlr'], QDir.Files | QDir.AllDirs | QDir.NoDotAndDotDot,QDir.Name):
                self.children.append(FileSystemItem(finfo, recurse))
        else:
            # file
            # Maybe get file contents?
            pass

    def filtered(self, filter):
        if not filter:
            return self

        namematch = filter.lower() in self.basename.lower() or filter.lower() in self.displayname.lower()
        if self.isdir:
            diritem = FileSystemItem(self.fullpath, False)
            for child in self.children:
                childmatch = child.filtered(filter)
                if childmatch is not None:
                    diritem.children.append((childmatch))
            # is dir a match?
            if namematch or len(diritem.children) > 0:
                return diritem
        else:
            if namematch:
                return FileSystemItem(self.fullpath, False)
            # TODO: Check file contents?
        return None
