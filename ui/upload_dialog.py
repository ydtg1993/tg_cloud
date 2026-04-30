from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QScrollArea, QWidget, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot

class UploadItem(QFrame):
    """代表一个上传文件的行"""
    def __init__(self, file_name, upload_id, parent=None):
        super().__init__(parent)
        self.upload_id = upload_id
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)

        layout = QVBoxLayout(self)
        # 第一行：文件名和状态
        top_layout = QHBoxLayout()
        self.name_label = QLabel(file_name)
        self.name_label.setWordWrap(True)
        self.status_label = QLabel("等待中")
        self.status_label.setStyleSheet("color: gray;")
        top_layout.addWidget(self.name_label, 1)
        top_layout.addWidget(self.status_label)
        layout.addLayout(top_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

    def set_status(self, text, color="gray"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def set_progress(self, value):
        self.progress_bar.setValue(value)

class UploadQueueDialog(QDialog):
    # 信号：所有任务完成
    all_finished = Signal()

    def __init__(self, file_paths, threadpool, upload_callback, parent=None):
        """
        file_paths: [(file_path, upload_id), ...]  upload_id 由主窗口生成
        threadpool: QThreadPool
        upload_callback: 函数，传入 (upload_id, file_path)，返回 UploadTask 对象，
                         并将任务的 finished/error 信号连接好
        """
        super().__init__(parent)
        self.setWindowTitle("文件上传队列")
        self.resize(500, 400)
        self.threadpool = threadpool
        self.upload_callback = upload_callback
        self.upload_items = {}          # upload_id -> UploadItem
        self.pending_tasks = 0
        self.completed_count = 0

        layout = QVBoxLayout(self)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.container)
        layout.addWidget(scroll)

        # 总体进度
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(QLabel("总进度："))
        self.global_progress = QProgressBar()
        self.global_progress.setRange(0, 0)   # 不确定进度，直到所有任务完成
        bottom_layout.addWidget(self.global_progress, 1)
        self.close_btn = QPushButton("关闭")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)
        layout.addLayout(bottom_layout)

        # 初始化条目
        for file_path, upload_id in file_paths:
            if upload_id not in self.upload_items:
                file_name = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
                item = UploadItem(file_name, upload_id)
                self.container_layout.addWidget(item)
                self.upload_items[upload_id] = item
                self.pending_tasks += 1

        self.global_progress.setRange(0, len(self.upload_items))
        self.global_progress.setValue(0)

    def start_uploads(self):
        """由主窗口调用，开始所有上传"""
        for upload_id, item in self.upload_items.items():
            # 从外部回调获取任务并连接信号
            # 这里我们需要让主窗口创建任务并连接，然后放入线程池
            # 我们采用一个更直接的方法：在创建对话框时传入所有任务信息，
            # 但任务需要信号连接。所以我们用回调产生任务并启动。
            pass  # 实际由主窗口在创建后逐个启动

    def on_task_started(self, upload_id):
        if upload_id in self.upload_items:
            self.upload_items[upload_id].set_status("上传中", "blue")
            self.upload_items[upload_id].set_progress(10)

    def on_task_finished(self, upload_id):
        if upload_id in self.upload_items:
            item = self.upload_items[upload_id]
            item.set_status("完成", "green")
            item.set_progress(100)
            self.completed_count += 1
            self.global_progress.setValue(self.completed_count)
            if self.completed_count == len(self.upload_items):
                self.close_btn.setEnabled(True)
                self.global_progress.setRange(0, 100)
                self.global_progress.setValue(100)
                self.all_finished.emit()

    def on_task_error(self, upload_id, error_msg):
        if upload_id in self.upload_items:
            item = self.upload_items[upload_id]
            item.set_status(f"失败: {error_msg}", "red")
            item.set_progress(0)
            self.completed_count += 1
            self.global_progress.setValue(self.completed_count)
            if self.completed_count == len(self.upload_items):
                self.close_btn.setEnabled(True)
                self.all_finished.emit()