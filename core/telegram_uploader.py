import os
from pyrogram import Client

WORK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sessions")

class PyrogramUploader:
    def __init__(self, session_string, api_id, api_hash):
        self.session_string = session_string
        self.api_id = api_id
        self.api_hash = api_hash

    async def upload(self, chat_id, file_path):
        client = Client(
            name="uploader",
            api_id=self.api_id,
            api_hash=self.api_hash,
            session_string=self.session_string,
            workdir=WORK_DIR
        )
        async with client:
            msg = await client.send_document(chat_id, file_path)
            return msg.document.file_id, msg.id