from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QFileInfo
from PySide6.QtWidgets import QApplication, QStyle, QFileIconProvider

class FileTableModel(QAbstractTableModel):
    HEADERS = ["名称", "大小", "修改时间", "类型"]
    # 文件图标提供器（利用系统注册表显示图标）
    _icon_provider = QFileIconProvider()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        is_dir = item[2]
        if role == Qt.DisplayRole:
            col = index.column()
            if col == 0:  # 名称
                return item[1] if is_dir else (item[5] or item[4])
            elif col == 1:  # 大小
                if is_dir:
                    return ""
                size = item[6]
                if size is None:
                    return ""
                try:
                    size = float(size)
                except (ValueError, TypeError):
                    return str(size)
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024:
                        return f"{size:.1f} {unit}"
                    size /= 1024
                return ""
            elif col == 2:  # 修改时间
                return "" if is_dir else item[7]
            elif col == 3:  # 类型
                if is_dir:
                    return "文件夹"
                return item[8] if item[8] else ""
        elif role == Qt.DecorationRole and index.column() == 0:
            if is_dir:
                return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            else:
                # 根据文件名获取系统关联图标
                name = item[5] or item[4]  # display_name 优先
                return self._get_system_icon(name)
        elif role == Qt.UserRole:
            return (item[0], is_dir)
        return None

    def _get_system_icon(self, filename):
        """通过文件扩展名获取系统关联图标，带简单缓存"""
        if not filename:
            return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        # 构造虚拟路径，仅用于获得图标
        suffix = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        # 为避免重复查询，可使用缓存字典（此处简单实现每次查询，性能影响很小）
        temp_path = f"temp.{suffix}" if suffix else "temp"
        icon = self._icon_provider.icon(QFileInfo(temp_path))
        if icon.isNull():
            return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        return icon

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