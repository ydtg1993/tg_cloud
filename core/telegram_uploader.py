import asyncio
from telegram import Bot
from telegram.error import TelegramError
import os

class BaseUploader:
    async def upload(self, token, chat_id, file_path):
        raise NotImplementedError

class BotApiUploader(BaseUploader):
    async def upload(self, token, chat_id, file_path):
        bot = Bot(token=token)
        async with bot:
            with open(file_path, 'rb') as f:
                message = await bot.send_document(chat_id=chat_id, document=f,
                                                  read_timeout=120, write_timeout=120)
            return message.document.file_id, message.message_id

class PyrogramUploader(BaseUploader):
    def __init__(self, session_string, api_id, api_hash):
        self.session_string = session_string
        self.api_id = api_id
        self.api_hash = api_hash

    async def upload(self, _, chat_id, file_path):
        from pyrogram import Client
        client = Client(":memory:", api_id=self.api_id, api_hash=self.api_hash,
                        session_string=self.session_string)
        async with client:
            msg = await client.send_document(chat_id, file_path)
            return msg.document.file_id, msg.id

def get_uploader(file_size, config):
    """根据文件大小选择上传器"""
    # Bot API 最大 50MB
    if file_size < 50 * 1024 * 1024:
        return BotApiUploader()
    else:
        pyro = config.get("pyrogram", {})
        if pyro.get("session_string"):
            return PyrogramUploader(
                pyro["session_string"],
                pyro.get("api_id"),
                pyro.get("api_hash")
            )
        else:
            raise Exception("大文件需要 Pyrogram 登录")