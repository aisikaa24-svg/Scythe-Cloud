import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load configuration from config.env
load_dotenv('config.env')

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

async def generate_string():
    # Use the existing local session file 'scythe_user_session'
    client = TelegramClient('scythe_user_session', API_ID, API_HASH)
    await client.connect()
    
    # Export to StringSession format
    string = StringSession.save(client.session)
    
    print("\n--- [ SHADOW CORE: SESSION STRING GENERATED ] ---")
    print("Copy the entire string below. Store it securely in your GitHub Secrets as 'SESSION_STRING'.")
    print("-" * 50)
    print(string)
    print("-" * 50)
    
    await client.disconnect()

if __name__ == '__main__':
    import asyncio
    asyncio.run(generate_string())
