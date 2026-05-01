from PySide6.QtCore import *

# ---------- 下载任务 ----------
class DownloadTask(QRunnable):
    class Signals(QObject):
        finished = Signal(str)
        error = Signal(str)
    def __init__(self, token, file_id, save_path):
        super().__init__()
        self.token = token
        self.file_id = file_id
        self.save_path = save_path
        self.signals = self.Signals()
    def run(self):
        try:
            import asyncio, aiohttp
            from telegram import Bot
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def _download():
                bot = Bot(token=self.token)
                async with bot:
                    file = await bot.get_file(self.file_id)
                    url = file.file_path
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            with open(self.save_path, 'wb') as f:
                                while True:
                                    chunk = await resp.content.read(8192)
                                    if not chunk: break
                                    f.write(chunk)
            loop.run_until_complete(_download())
            self.signals.finished.emit(self.save_path)
        except Exception as e:
            self.signals.error.emit(str(e))

# ---------- 删除任务 ----------
class DeleteMessageTask(QRunnable):
    class Signals(QObject):
        finished = Signal()
        error = Signal(str)
    def __init__(self, token, chat_id, message_id):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.message_id = message_id
        self.signals = self.Signals()
    def run(self):
        try:
            from telegram import Bot
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def _delete():
                bot = Bot(token=self.token)
                async with bot:
                    await bot.delete_message(chat_id=self.chat_id, message_id=self.message_id)
            loop.run_until_complete(_delete())
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))