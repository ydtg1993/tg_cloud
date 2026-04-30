import os
import asyncio
from PySide6.QtCore import QRunnable, Signal, QObject
from core.telegram_uploader import get_uploader

class UploadSignals(QObject):
    progress = Signal(str, int)        # upload_id, 百分比 (0-100)
    finished = Signal(str, str, int, str, int)  # upload_id, file_id, msg_id, original_name, file_size
    error = Signal(str, str)          # upload_id, error_msg

class UploadTask(QRunnable):
    def __init__(self, token, chat_id, file_path, config, upload_id, is_temp=False):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.file_path = file_path
        self.config = config
        self.upload_id = upload_id      # 用于关联对话框条目
        self.is_temp = is_temp
        self.signals = UploadSignals()

    def run(self):
        try:
            # 发送开始进度
            self.signals.progress.emit(self.upload_id, 10)
            size = os.path.getsize(self.file_path)
            uploader = get_uploader(size, self.config)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            file_id, msg_id = loop.run_until_complete(
                uploader.upload(self.token, self.chat_id, self.file_path)
            )
            # 完成
            self.signals.progress.emit(self.upload_id, 100)
            self.signals.finished.emit(self.upload_id, file_id, msg_id,
                                       os.path.basename(self.file_path), size)
        except Exception as e:
            self.signals.error.emit(self.upload_id, str(e))