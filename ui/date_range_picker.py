from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialogButtonBox, QDateEdit
from PySide6.QtCore import QDate, Signal

class DateRangePickerDialog(QDialog):
    date_range_selected = Signal(str, str)  # start_date, end_date

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择时间范围")
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 日期选择器
        date_layout = QHBoxLayout()
        start_label = QLabel("起始日期:")
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-7))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")

        end_label = QLabel("结束日期:")
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")

        date_layout.addWidget(start_label)
        date_layout.addWidget(self.start_date_edit)
        date_layout.addWidget(end_label)
        date_layout.addWidget(self.end_date_edit)
        layout.addLayout(date_layout)

        # 快捷选择
        quick_layout = QHBoxLayout()
        today_btn = QPushButton("今天")
        today_btn.clicked.connect(lambda: self._set_quick_range(0))
        week_btn = QPushButton("最近7天")
        week_btn.clicked.connect(lambda: self._set_quick_range(7))
        month_btn = QPushButton("最近30天")
        month_btn.clicked.connect(lambda: self._set_quick_range(30))
        quick_layout.addWidget(today_btn)
        quick_layout.addWidget(week_btn)
        quick_layout.addWidget(month_btn)
        layout.addLayout(quick_layout)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_quick_range(self, days):
        today = QDate.currentDate()
        if days == 0:
            self.start_date_edit.setDate(today)
            self.end_date_edit.setDate(today)
        else:
            self.start_date_edit.setDate(today.addDays(-days))
            self.end_date_edit.setDate(today)

    def _accept(self):
        start = self.start_date_edit.date().toString("yyyy-MM-dd")
        end = self.end_date_edit.date().toString("yyyy-MM-dd")
        if start > end:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "提示", "起始日期不能大于结束日期")
            return
        self.date_range_selected.emit(start, end)
        self.accept()