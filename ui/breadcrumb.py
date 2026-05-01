from PySide6.QtCore import Qt
from PySide6.QtWidgets import *

class BreadcrumbNavigator:
    def __init__(self, breadcrumb_layout, db, directory_change_callback):
        self.layout = breadcrumb_layout
        self.db = db
        self.on_directory_change = directory_change_callback   # (dir_id) -> None
        self.current_dir_id = 0

    def update(self, dir_id):
        self.current_dir_id = dir_id
        layout = self.layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        path = self.db.get_path_to_directory(dir_id)
        for i, (d_id, name) in enumerate(path):
            if i > 0:
                sep = QLabel(">")
                sep.setStyleSheet("color: #888;")
                layout.addWidget(sep)
            btn = QPushButton(name)
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            if d_id == dir_id:
                btn.setStyleSheet("font-weight: bold; color: #fff; border: none; background: transparent; padding: 2px 6px;")
            else:
                btn.setStyleSheet("color: #ccc; border: none; background: transparent; padding: 2px 6px;")
            btn.clicked.connect(lambda checked, d=d_id: self.on_directory_change(d))
            layout.addWidget(btn)
        layout.addStretch()