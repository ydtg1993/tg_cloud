from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex

class FileTableModel(QAbstractTableModel):
    HEADERS = ["名称", "大小", "上传时间", "类型"]
    def __init__(self, parent=None):
        super().__init__(parent)
        self._files = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._files)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        file = self._files[row]
        if role == Qt.DisplayRole:
            col = index.column()
            if col == 0:
                # display_name 或 original_name
                return file[3] if file[3] else file[2]
            elif col == 1:
                size = file[4]
                if size is None:
                    return ""
                # 强制转换为 float/int 以防数据库返回字符串
                try:
                    size = float(size)
                except (ValueError, TypeError):
                    return str(size)
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024:
                        return f"{size:.1f} {unit}"
                    size /= 1024
            elif col == 2:
                return file[5]  # upload_time
            elif col == 3:
                return file[6]  # mime_type
        elif role == Qt.UserRole:
            return file[0]  # local id
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def load_files(self, files):
        self.beginResetModel()
        self._files = files
        self.endResetModel()

    def get_file_info(self, row):
        return self._files[row]