from PySide6.QtCore import Qt, QModelIndex, QPersistentModelIndex
from PySide6.QtWidgets import QTreeView
from PySide6.QtGui import QColor
from core.drag_service import DragDataService

class DirTreeView(QTreeView):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setDragDropMode(QTreeView.DropOnly)
        self.setAcceptDrops(True)
        self.file_moved_callback = None
        self._highlight_index = QModelIndex()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(DragDataService.MIME_TYPE):
            event.acceptProposedAction()
            self._update_highlight(event.pos())
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(DragDataService.MIME_TYPE):
            event.acceptProposedAction()
            self._update_highlight(event.pos())
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._clear_highlight()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._clear_highlight()
        if event.mimeData().hasFormat(DragDataService.MIME_TYPE):
            index = self.indexAt(event.pos())
            if not index.isValid():
                return
            dir_id = index.data(Qt.UserRole)
            file_ids = DragDataService.decode_file_ids(event.mimeData())
            if self.file_moved_callback:
                for fid in file_ids:
                    self.file_moved_callback(fid, dir_id)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _update_highlight(self, pos):
        index = self.indexAt(pos)
        if self._highlight_index.isValid():
            self.model().setData(self._highlight_index, QColor(), Qt.BackgroundRole)
            self._highlight_index = QModelIndex()
        if index.isValid():
            self.model().setData(index, QColor(100, 149, 237, 80), Qt.BackgroundRole)
            self._highlight_index = QPersistentModelIndex(index)

    def _clear_highlight(self):
        if self._highlight_index.isValid():
            self.model().setData(self._highlight_index, QColor(), Qt.BackgroundRole)
            self._highlight_index = QModelIndex()