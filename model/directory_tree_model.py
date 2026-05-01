from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

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