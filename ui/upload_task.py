import os
import asyncio
from PySide6.QtCore import QRunnable, Signal, QObject
from core.telegram_uploader import PyrogramUploader


class UploadSignals(QObject):
    finished = Signal(str, str, int, str, int)  # upload_id, file_id, msg_id, original_name, file_size
    error = Signal(str, str)          # upload_id, error_msg

class UploadTask(QRunnable):
    def __init__(self, session_string, api_id, api_hash, chat_id, file_path, upload_id):
        super().__init__()
        self.session_string = session_string
        self.api_id = api_id
        self.api_hash = api_hash
        self.chat_id = chat_id
        self.file_path = file_path
        self.upload_id = upload_id
        self.signals = UploadSignals()

    def run(self):
        try:
            size = os.path.getsize(self.file_path)
            uploader = PyrogramUploader(self.session_string, self.api_id, self.api_hash)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            file_id, msg_id = loop.run_until_complete(
                uploader.upload(self.chat_id, self.file_path)
            )
            self.signals.finished.emit(self.upload_id, file_id, msg_id,
                                       os.path.basename(self.file_path), size)
        except Exception as e:
            self.signals.error.emit(self.upload_id, str(e))