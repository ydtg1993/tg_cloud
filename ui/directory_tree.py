from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeView

class DirectoryTreeModel(QStandardItemModel):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setHorizontalHeaderLabels(["目录"])
        self.root_item = self.invisibleRootItem()
        self.refresh()

    def refresh(self):
        self.removeRows(0, self.rowCount())
        dirs = self.db.get_directories(parent_id=0)
        for d in dirs:
            item = QStandardItem(d[1])
            item.setData(d[0], Qt.UserRole)  # id
            item.setEditable(False)
            self.root_item.appendRow(item)
            self._add_children(item, d[0])

    def _add_children(self, parent_item, parent_id):
        children = self.db.get_directories(parent_id)
        for child in children:
            item = QStandardItem(child[1])
            item.setData(child[0], Qt.UserRole)
            item.setEditable(False)
            parent_item.appendRow(item)
            self._add_children(item, child[0])

    def add_directory(self, name, parent_id=0):
        self.db.add_directory(name, parent_id)
        self.refresh()

class DirTreeView(QTreeView):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setDragDropMode(QTreeView.DropOnly)
        self.setAcceptDrops(True)
        self.file_moved_callback = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-id"):
            index = self.indexAt(event.pos())
            if not index.isValid():
                return
            dir_id = index.data(Qt.UserRole)
            # 解析 file_id
            raw_data = bytes(event.mimeData().data("application/x-file-id"))
            file_local_id = int(raw_data.decode())   # 我们存的是字符串
            if self.file_moved_callback:
                self.file_moved_callback(file_local_id, dir_id)
            event.acceptProposedAction()
        else:
            event.ignore()