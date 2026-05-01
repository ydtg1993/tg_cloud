from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class FileTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.move_file_callback = None   # 主窗口设置
        self._highlight_row = -1

    def startDrag(self, supportedActions):
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return
        idx = indexes[0]
        file_model = self.model()
        if not hasattr(file_model, 'get_item'):
            super().startDrag(supportedActions)
            return
        item = file_model.get_item(idx.row())
        if not item or item[2] != 0:  # 不是文件
            return
        file_id = item[0]
        mime = QMimeData()
        mime.setData("application/x-file-id", str(file_id).encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        # 设置拖拽图标
        icon = idx.data(Qt.DecorationRole)
        if icon and hasattr(icon, 'pixmap'):
            drag.setPixmap(icon.pixmap(48, 48))
        else:
            # 默认图标
            drag.setPixmap(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(48, 48))
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-id"):
            event.acceptProposedAction()
            self._update_highlight(event.pos())
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-file-id"):
            event.acceptProposedAction()
            self._update_highlight(event.pos())
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._clear_highlight()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._clear_highlight()
        if event.mimeData().hasFormat("application/x-file-id"):
            target_index = self.indexAt(event.pos())
            if not target_index.isValid():
                return
            file_model = self.model()
            if not hasattr(file_model, 'get_item'):
                return
            item = file_model.get_item(target_index.row())
            if not item or item[2] != 1:  # 不是目录
                return
            target_dir_id = item[0]
            raw = bytes(event.mimeData().data("application/x-file-id"))
            file_local_id = int(raw.decode())
            if self.move_file_callback:
                self.move_file_callback(file_local_id, target_dir_id)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def _update_highlight(self, pos):
        index = self.indexAt(pos)
        model = self.model()
        if self._highlight_row >= 0:
            model.setData(model.index(self._highlight_row, 0), QColor(), Qt.BackgroundRole)
            self._highlight_row = -1

        if index.isValid():
            item = model.get_item(index.row())
            if item and item[2] == 1:  # 是目录行
                model.setData(index, QColor(100, 149, 237, 80), Qt.BackgroundRole)
                self._highlight_row = index.row()

    def _clear_highlight(self):
        if self._highlight_row >= 0:
            model = self.model()
            model.setData(model.index(self._highlight_row, 0), QColor(), Qt.BackgroundRole)
            self._highlight_row = -1