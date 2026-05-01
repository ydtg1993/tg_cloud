from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json

class FileTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.move_file_callback = None
        self._highlight_row = -1
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start_pos is not None:
            # 检查是否达到拖拽阈值（避免轻微抖动导致误拖拽）
            if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                index = self.indexAt(self._drag_start_pos)
                if index.isValid():
                    model = self.model()
                    if hasattr(model, 'get_item'):
                        item = model.get_item(index.row())
                        if item and item[2] == 0:  # 是文件
                            # 启动拖拽（内部会收集所有选中的文件）
                            self._start_multidrag()
                            self._drag_start_pos = None
                            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _start_multidrag(self):
        """收集所有选中的文件 ID 并启动拖拽"""
        indexes = self.selectionModel().selectedRows()
        file_ids = []
        model = self.model()
        if not hasattr(model, 'get_item'):
            return
        # 收集所有选中的文件 ID（忽略目录）
        for idx in indexes:
            item = model.get_item(idx.row())
            if item and item[2] == 0:
                file_ids.append(item[0])
        if not file_ids:
            return

        # 序列化为 JSON
        import json
        mime = QMimeData()
        mime.setData("application/x-file-id", json.dumps(file_ids).encode())

        drag = QDrag(self)
        drag.setMimeData(mime)

        # 图标使用第一个文件的图标
        first_idx = indexes[0]
        icon = first_idx.data(Qt.DecorationRole)
        if icon and hasattr(icon, 'pixmap'):
            drag.setPixmap(icon.pixmap(48, 48))
        else:
            drag.setPixmap(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(48, 48))
        drag.exec(Qt.MoveAction)

    def startDrag(self, supportedActions):
        self._start_multidrag()

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
            if not item or item[2] != 1:
                return
            target_dir_id = item[0]
            raw_data = bytes(event.mimeData().data("application/x-file-id"))
            try:
                file_ids = json.loads(raw_data.decode())
                if isinstance(file_ids, int):
                    file_ids = [file_ids]
            except:
                file_ids = [int(raw_data.decode())]

            if self.move_file_callback:
                for fid in file_ids:
                    self.move_file_callback(fid, target_dir_id)
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