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
MESSAGE_PROCESS_LIMIT = 500 # Optimized for high-volume unread catch-up
MIN_DELAY = 10.0
MAX_DELAY = 30.0
CHAT_TRANSITION_DELAY = (1, 3) # Minutes
SYNC_THRESHOLD_HOURS = 12 # Only send to Bot/Supabase every 12 hours

# Regex for card patterns (supports |, /, space, :, -)
CARD_REGEX = r'(\d{14,16})(?:[\s/|:-]+)(\d{1,2})(?:[\s/|:-]+)(\d{2,4})(?:(?:[\s/|:-]+)(\d{3,4}))?'

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
    # 1. Supabase Sync (Atomic Card Storage)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    for card in cards:
        try:
            supabase.table("cards").upsert({"card_data": card}).execute()
        except: pass
    
    # 2. Telegram Bot File (Consolidated Intel)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp:
            tmp.write("\n".join(cards))
            tmp_path = tmp.name
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        with open(tmp_path, 'rb') as f:
            files = {'document': ('scythe_vectors.txt', f)}
            caption = f"🎯 MISSION SUCCESS: {len(cards)} Intelligence Vectors Extracted.\n[Cycle: 12H | Stealth: Iron-Clad]"
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            requests.post(url, data=data, files=files)
        os.unlink(tmp_path)

def obfuscate_card_number(original):
    if len(original) < 13: return original
    base = original[:12]
    mid = "".join([str(random.randint(0, 9)) for _ in range(3)])
    prefix = base + mid
    digits = [int(d) for d in prefix]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 0:
            d *= 2
            if d > 9: d -= 9
        checksum += d
    check_digit = (10 - (checksum % 10)) % 10
    return prefix + str(check_digit)

async def cloud_mission():
    print("--- [ Project SCYTHE: CLOUD CYCLE INITIATED ] ---")
    
    # --- HUMAN SIMULATION PROTOCOL (SHΔDØW HUM-SIM) ---
    # Randomized Start Jitter (1-10 minutes) to avoid fixed patterns
    jitter = random.randint(60, 600)
    print(f"Shadow Initialization Jitter: Waiting {jitter}s...")
    await asyncio.sleep(jitter)

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
    
    print(f"Intelligence Grid: {len(all_dialogs)} channels with unread intel.")
    
    # SHΔDØW HUM-SIM: Randomly shuffle targets so every cycle is different
    random.shuffle(all_dialogs)
    print("Targets shuffled for Stealth Recon.")
    
    new_cards = []
    
    for dialog in all_dialogs:
        last_id = state.get_last_id(dialog.id)
        # Limit processed messages per cycle to stay safe
        limit = min(dialog.unread_count, MESSAGE_PROCESS_LIMIT)
        print(f"Scrubbing: {dialog.name} ({limit} messages)")
        
        processed = 0
        current_max = last_id
        
        async for msg in client.iter_messages(dialog.id, limit=limit):
            processed += 1
            if msg.id > current_max: current_max = msg.id
            
            if msg.text:
                matches = re.findall(CARD_REGEX, msg.text)
                for groups in matches:
                    # Groups: (Number, Month, Year, [CVV])
                    if len(groups) >= 3:
                        num = groups[0].strip()
                        # Network Filter
                        if not num.startswith(('4', '5')): continue
                        # Luhn Check
                        if not is_luhn_valid(num): continue
                        
                        # Sanitization Protocol
                        obfuscated = obfuscate_card_number(num)
                        month = groups[1].strip()
                        if len(month) == 1: month = "0" + month
                        year = groups[2].strip()
                        if len(year) == 2: year = "20" + year
                        
                        orig_cvv = groups[3].strip() if len(groups) > 3 and groups[3] else ""
                        cvv = orig_cvv if len(orig_cvv) == 3 else "".join([str(random.randint(0, 9)) for _ in range(3)])
                        
                        new_cards.append(f"{obfuscated}|{month}|{year}|{cvv}")
            
            if processed % 50 == 0:
                await asyncio.sleep(2) # Micro-throttle

        state.update_last_id(dialog.id, current_max)
        await client.send_read_acknowledge(dialog.id, max_id=current_max)

        if len(new_cards) > 0:
            state.stage_cards(new_cards)
            new_cards = []

        # Inter-target delay (SHΔDØW Adaptive Stealth)
        # Simulation: Moving from one channel to another after "reading"
        wait = random.uniform(45, 120) # 0.75 to 2 mins
        print(f"  > Mission Synchronized. Transitioning targets in {int(wait)}s...")
        await asyncio.sleep(wait)

    # FINAL DELIVERY: Every 12H mission sends the consolidated file
    staged = state.get_staged_cards()
    if staged:
        await sync_to_targets(staged)
        state.clear_staged_cards()
        # Unlock the scraper in Supabase for the next mission
        try:
            create_client(SUPABASE_URL, SUPABASE_KEY).table("system_settings").upsert({"key": "scraper_locked", "value": "false"}).execute()
        except:
            print("Cleanup Warning: Mission completed but Supabase unlock pending due to connection glitch.")
    else:
        print("Intelligence Grid Clean: No new vectors detected.")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(cloud_mission())
