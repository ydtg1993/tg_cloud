from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from core.utils import format_file_size

class SearchResultDialog(QDialog):
    file_selected = Signal(int, int)

    def __init__(self, results, search_type="文件名", parent=None):
        super().__init__(parent)
        self.results = results
        self.search_type = search_type
        self.setWindowTitle(f"{search_type}搜索结果 - 共 {len(results)} 个文件")
        self.resize(700, 500)
        self._setup_ui()
        self._populate_results()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        title_label = QLabel(f"找到 {len(self.results)} 个文件")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["文件名", "路径", "上传时间"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.jump_btn = QPushButton("📂 跳转到文件所在目录")
        self.jump_btn.clicked.connect(self._on_jump_clicked)
        self.jump_btn.setEnabled(False)
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.jump_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_jump_clicked)

    def _populate_results(self):
        self.table.setRowCount(len(self.results))
        for row, result in enumerate(self.results):
            name_item = QTableWidgetItem(result['name'])
            name_item.setData(Qt.UserRole, result['id'])
            name_item.setToolTip(f"ID: {result['id']}\n大小: {format_file_size(result['file_size'])}")
            self.table.setItem(row, 0, name_item)

            path_item = QTableWidgetItem(result['full_path'])
            path_item.setToolTip(result['full_path'])
            self.table.setItem(row, 1, path_item)

            time_str = result['upload_time'] if result['upload_time'] else "未知"
            time_item = QTableWidgetItem(time_str)
            self.table.setItem(row, 2, time_item)

        self.table.sortItems(0, Qt.AscendingOrder)

    def _on_selection_changed(self):
        self.jump_btn.setEnabled(len(self.table.selectedItems()) > 0)

    def _on_jump_clicked(self):
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows:
            return
        row = next(iter(selected_rows))
        result = self.results[row]
        self.file_selected.emit(result['id'], result['directory_id'])
        self.accept()