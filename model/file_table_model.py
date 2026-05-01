from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import QApplication, QStyle
from PySide6.QtGui import QColor
from ui.icon_manager import IconManager
from core.utils import format_file_size

class FileTableModel(QAbstractTableModel):
    HEADERS = ["名称", "大小", "修改时间", "类型"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []          # 存储 DirectoryItem 对象
        self._backgrounds = {}

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        item = self._items[row]
        if role == Qt.BackgroundRole:
            return self._backgrounds.get(row)
        if role == Qt.DisplayRole:
            col = index.column()
            if col == 0:  # 名称
                return item.name if item.is_dir else (item.display_name or item.original_name)
            elif col == 1:  # 大小
                if item.is_dir:
                    return ""
                return format_file_size(item.file_size)
            elif col == 2:  # 修改时间
                return "" if item.is_dir else (item.upload_time or "")
            elif col == 3:  # 类型
                if item.is_dir:
                    return "文件夹"
                return item.mime_type or ""
        elif role == Qt.DecorationRole and index.column() == 0:
            if item.is_dir:
                return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            else:
                name = item.display_name or item.original_name
                return IconManager.get_icon(name)
        elif role == Qt.UserRole:
            return (item.id, item.is_dir)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.BackgroundRole:
            row = index.row()
            if value is None or (isinstance(value, QColor) and not value.isValid()):
                self._backgrounds.pop(row, None)
            else:
                self._backgrounds[row] = value
            self.dataChanged.emit(index, index, [Qt.BackgroundRole])
            return True
        return super().setData(index, value, role)

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def load_items(self, items):
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def get_item(self, row):
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def flags(self, index):
        default_flags = super().flags(index)
        if not index.isValid():
            return default_flags
        item = self._items[index.row()]
        if item.is_dir == 0:  # 是文件
            default_flags |= Qt.ItemIsDragEnabled
        default_flags |= Qt.ItemIsDropEnabled
        return default_flags