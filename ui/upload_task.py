import os
import asyncio
from PySide6.QtCore import QRunnable, Signal, QObject
from core.telegram_uploader import get_uploader

class UploadSignals(QObject):
    progress = Signal(int)                          # 单文件进度百分比
    finished = Signal(str, str, int, str, int)      # local_temp_id, file_id, message_id, original_name, file_size
    error = Signal(str, str)                        # local_temp_id, error_msg

class UploadTask(QRunnable):
    def __init__(self, token, chat_id, file_path, config, local_temp_id, is_temp=False):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.file_path = file_path
        self.config = config
        self.local_temp_id = local_temp_id
        self.is_temp = is_temp          # 标记是否为临时文件（剪贴板截图）
        self.signals = UploadSignals()

    def run(self):
        try:
            size = os.path.getsize(self.file_path)
            uploader = get_uploader(size, self.config)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            file_id, msg_id = loop.run_until_complete(
                uploader.upload(self.token, self.chat_id, self.file_path)
            )
            self.signals.finished.emit(
                self.local_temp_id, file_id, msg_id,
                os.path.basename(self.file_path), size
            )
        except Exception as e:
            self.signals.error.emit(self.local_temp_id, str(e))