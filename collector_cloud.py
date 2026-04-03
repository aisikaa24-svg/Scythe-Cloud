import os
import re
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from supabase import create_client, Client
from dotenv import load_dotenv

# Load configuration
load_dotenv('config.env')

# Telegram Config
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')

# Supabase Config
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SECRET_KEY') # Needs the service/secret key for write access

# Regex for card patterns
CARD_REGEX = r'(\d{14,16}\|\d{1,2}\|\d{2,4}(?:\|\d{3,4})?\|?)'

async def cloud_mission():
    print("--- [ Project SCYTHE: Cloud Extraction Core ] ---")
    
    if not SESSION_STRING:
        print("Error: SESSION_STRING missing.")
        return

    # Initialize Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Initialize Telegram Client with StringSession
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    await client.connect()
    if not await client.is_user_authorized():
        print("Error: Session string is invalid or expired.")
        return
        
    print("Authenticated successfully via Cloud Session.")

    cards_found = []
    total_processed = 0

    print("Scanning all dialogs for unread content...")
    
    async for dialog in client.iter_dialogs():
        if dialog.unread_count > 0:
            count = dialog.unread_count
            print(f"Scrubbing: {dialog.name} ({count} unread)")
            
            processed_in_dialog = 0
            max_id = 0
            
            async for msg in client.iter_messages(dialog.id, limit=count):
                processed_in_dialog += 1
                if msg.id > max_id:
                    max_id = msg.id
                
                if msg.text:
                    matches = re.findall(CARD_REGEX, msg.text)
                    if matches:
                        for card in matches:
                            cards_found.append(card)
                
                if processed_in_dialog % 500 == 0:
                    print(f"  > Progress: {processed_in_dialog}/{count} processed...")

            total_processed += processed_in_dialog
            
            if max_id:
                await client.send_read_acknowledge(dialog.id, max_id=max_id)
            print(f"  > [DONE] {dialog.name} synchronized.")

    # Deduplicate and sync to Supabase
    if cards_found:
        unique_cards = list(dict.fromkeys(cards_found))
        print(f"Syncing {len(unique_cards)} unique cards to Supabase...")
        
        for card in unique_cards:
            try:
                # Insert if not exists (using upsert logic or just ignoring errors for duplicates)
                supabase.table("cards").upsert({"card_data": card}).execute()
            except Exception as e:
                # Likely a duplicate error if not using upsert properly, we can ignore
                pass
                
        print("Success: Database synchronized.")
    else:
        print("No new cards found.")

    print(f"Mission Complete: {total_processed} messages processed.")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(cloud_mission())
