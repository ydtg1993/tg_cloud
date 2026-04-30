import asyncio
from pyrogram import Client

async def login_pyrogram(api_id, api_hash, phone_number):
    client = Client(":memory:", api_id=api_id, api_hash=api_hash)
    await client.connect()
    code = await client.send_code(phone_number)
    # 这里需要交互输入验证码，为简化GUI中弹出输入框
    # 先返回 client 和 phone_code_hash，在 GUI 中处理
    return client, code.phone_code_hash

async def finish_login(client, phone_number, phone_code_hash, code):
    await client.sign_in(phone_number, phone_code_hash, code)
    session_string = await client.export_session_string()
    await client.disconnect()
    return session_string