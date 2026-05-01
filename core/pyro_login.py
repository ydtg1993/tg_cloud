import asyncio
import os
from pyrogram import Client

# 统一的工作目录，避免权限问题
WORK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sessions")
os.makedirs(WORK_DIR, exist_ok=True)   # 自动创建 sessions 文件夹

async def login_pyrogram(api_id, api_hash, phone_number):
    client = Client(
        name="my_account",             # 使用具体名称，不推荐 :memory:
        api_id=api_id,
        api_hash=api_hash,
        workdir=WORK_DIR               # 指定工作目录，确保可写
    )
    await client.connect()
    code = await client.send_code(phone_number)
    return client, code.phone_code_hash

async def finish_login(client, phone_number, phone_code_hash, code):
    await client.sign_in(phone_number, phone_code_hash, code)
    session_string = await client.export_session_string()
    await client.disconnect()
    return session_string