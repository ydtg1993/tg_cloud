from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QScrollArea, QWidget, QFrame
)
from PySide6.QtCore import Qt, Signal, QFileInfo
from PySide6.QtWidgets import QFileIconProvider

class UploadItem(QFrame):
    def __init__(self, file_path, upload_id, parent=None):
        super().__init__(parent)
        self.upload_id = upload_id
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)

        layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()

        # 文件图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        info = QFileInfo(file_path)
        self.icon_label.setPixmap(QFileIconProvider().icon(info).pixmap(24, 24))
        top_layout.addWidget(self.icon_label)

        # 文件名
        self.name_label = QLabel(file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1])
        self.name_label.setWordWrap(True)
        self.status_label = QLabel("等待中")
        self.status_label.setStyleSheet("color: gray;")
        top_layout.addWidget(self.name_label, 1)
        top_layout.addWidget(self.status_label)
        layout.addLayout(top_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

    def set_status(self, text, color="gray"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def set_progress(self, value):
        self.progress_bar.setValue(value)

class UploadQueueDialog(QDialog):
    all_finished = Signal()

    def __init__(self, file_paths, parent=None):
        """
        file_paths: [(full_path, upload_id), ...]
        """
        super().__init__(parent)
        self.setWindowTitle("文件上传队列")
        self.resize(500, 400)
        self.upload_items = {}
        self.total = len(file_paths)
        self.completed = 0

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.global_progress = QProgressBar()
        self.global_progress.setRange(0, self.total)
        self.global_progress.setValue(0)
        layout.addWidget(QLabel("总进度："))
        layout.addWidget(self.global_progress)

        self.close_btn = QPushButton("关闭")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        for file_path, upload_id in file_paths:
            item = UploadItem(file_path, upload_id)
            self.container_layout.addWidget(item)
            self.upload_items[upload_id] = item

    def task_started(self, upload_id):
        if upload_id in self.upload_items:
            item = self.upload_items[upload_id]
            item.set_status("上传中", "blue")
            item.progress_bar.setRange(0, 0)      # 忙碌模式
            item.progress_bar.setValue(0)

    def task_finished(self, upload_id):
        if upload_id in self.upload_items:
            item = self.upload_items[upload_id]
            item.set_status("完成", "green")
            item.progress_bar.setRange(0, 100)    # 恢复正常
            item.progress_bar.setValue(100)
            self._one_done()

    def task_error(self, upload_id, error_msg):
        if upload_id in self.upload_items:
            item = self.upload_items[upload_id]
            item.set_status(f"失败: {error_msg}", "red")
            item.progress_bar.setRange(0, 100)    # 恢复正常
            item.progress_bar.setValue(0)
            self._one_done()

    def _one_done(self):
        self.completed += 1
        self.global_progress.setValue(self.completed)
        if self.completed == self.total:
            self.close_btn.setEnabled(True)
            self.all_finished.emit()