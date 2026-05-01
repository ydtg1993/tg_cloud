from PySide6.QtCore import *
import os
from pyrogram import Client
import asyncio

WORK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sessions")

class DownloadTask(QRunnable):
    # ... 内部创建 Client 时需传入 workdir=WORK_DIR
    class Signals(QObject):
        finished = Signal(str)
        error = Signal(str)

    def __init__(self, session_string, api_id, api_hash, file_id, save_path):
        super().__init__()
        self.session_string = session_string
        self.api_id = api_id
        self.api_hash = api_hash
        self.file_id = file_id
        self.save_path = save_path
        self.signals = self.Signals()

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def _download():
                client = Client("downloader", session_string=self.session_string,
                                api_id=self.api_id, api_hash=self.api_hash,
                                workdir=WORK_DIR)
                async with client:
                    await client.download_media(self.file_id, file_name=self.save_path)
            loop.run_until_complete(_download())
            self.signals.finished.emit(self.save_path)
        except Exception as e:
            self.signals.error.emit(str(e))

class DeleteMessageTask(QRunnable):
    # ... 同理
    class Signals(QObject):
        finished = Signal()
        error = Signal(str)

    def __init__(self, session_string, api_id, api_hash, chat_id, message_id):
        super().__init__()
        self.session_string = session_string
        self.api_id = api_id
        self.api_hash = api_hash
        self.chat_id = chat_id
        self.message_id = message_id
        self.signals = self.Signals()

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def _delete():
                client = Client("deleter", session_string=self.session_string,
                                api_id=self.api_id, api_hash=self.api_hash,
                                workdir=WORK_DIR)
                async with client:
                    await client.delete_messages(self.chat_id, self.message_id)
            loop.run_until_complete(_delete())
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))