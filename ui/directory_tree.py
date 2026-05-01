from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QTreeView
from PySide6.QtGui import QColor
from PySide6.QtCore import QPersistentModelIndex
import json

class DirTreeView(QTreeView):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setDragDropMode(QTreeView.DropOnly)
        self.setAcceptDrops(True)
        self.file_moved_callback = None
        self._highlight_index = QModelIndex()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-id"):
            event.acceptProposedAction()
            # 允许时立即更新高亮
            self._update_highlight(event.pos())
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-id"):
            event.acceptProposedAction()
            self._update_highlight(event.pos())
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._clear_highlight()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._clear_highlight()
        if event.mimeData().hasFormat("application/x-file-id"):
            index = self.indexAt(event.pos())
            if not index.isValid():
                return
            dir_id = index.data(Qt.UserRole)
            raw_data = bytes(event.mimeData().data("application/x-file-id"))
            try:
                file_ids = json.loads(raw_data.decode())
                if isinstance(file_ids, int):  # 兼容旧格式
                    file_ids = [file_ids]
            except:
                file_ids = [int(raw_data.decode())]

            if self.file_moved_callback:
                for fid in file_ids:
                    self.file_moved_callback(fid, dir_id)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _update_highlight(self, pos):
        index = self.indexAt(pos)
        # 清除上一个高亮
        if self._highlight_index.isValid():
            self.model().setData(self._highlight_index, QColor(), Qt.BackgroundRole)
            self._highlight_index = QModelIndex()

        if index.isValid():
            # 只有目录项才高亮（所有项都是目录，所以可直接高亮）
            self.model().setData(index, QColor(100, 149, 237, 80), Qt.BackgroundRole)  # 矢车菊蓝半透明
            # 为确保视图刷新，使用 QPersistentModelIndex
            self._highlight_index = QPersistentModelIndex(index)

    def _clear_highlight(self):
        if self._highlight_index.isValid():
            self.model().setData(self._highlight_index, QColor(), Qt.BackgroundRole)
            self._highlight_index = QModelIndex()