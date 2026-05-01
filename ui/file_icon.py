from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from core.drag_service import DragDataService

class FileIconView(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.move_file_callback = None
        self._highlight_item = None

    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        file_ids = []
        for item in selected_items:
            data = item.data(Qt.UserRole)
            if data and data[1] == 0:
                file_ids.append(data[0])
        if not file_ids:
            return

        mime = DragDataService.encode_file_ids(file_ids)
        drag = QDrag(self)
        drag.setMimeData(mime)
        if selected_items:
            drag.setPixmap(selected_items[0].icon().pixmap(48, 48))
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(DragDataService.MIME_TYPE):
            event.acceptProposedAction()
            self._update_highlight(event.pos())
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(DragDataService.MIME_TYPE):
            event.acceptProposedAction()
            self._update_highlight(event.pos())
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._clear_highlight()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._clear_highlight()
        if event.mimeData().hasFormat(DragDataService.MIME_TYPE):
            item = self.itemAt(event.pos())
            if not item:
                return
            data = item.data(Qt.UserRole)
            if not data or data[1] != 1:
                return
            target_dir_id = data[0]
            file_ids = DragDataService.decode_file_ids(event.mimeData())
            if self.move_file_callback:
                for fid in file_ids:
                    self.move_file_callback(fid, target_dir_id)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def _update_highlight(self, pos):
        self._clear_highlight()
        item = self.itemAt(pos)
        if item:
            data = item.data(Qt.UserRole)
            if data and data[1] == 1:
                item.setBackground(QColor(100, 149, 237, 80))
                self._highlight_item = item

    def _clear_highlight(self):
        if self._highlight_item:
            self._highlight_item.setBackground(QColor())
            self._highlight_item = None