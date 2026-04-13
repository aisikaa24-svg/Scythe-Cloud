import os
import re
import asyncio
import random
from telethon import TelegramClient, events
from dotenv import load_dotenv
from state_manager import StateManager
from datetime import datetime

# Load configuration from config.env
load_dotenv('config.env')

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# Regex for card patterns
CARD_REGEX = r'(\d{14,16}\|\d{1,2}\|\d{2,4}(?:\|\d{3,4})?\|?)'

# --- STEALTH CONFIGURATION ---
BATCH_CHAT_LIMIT = random.randint(3, 6)  # Only process 3-6 chats per run
MESSAGE_PROCESS_LIMIT = random.randint(10, 20) # Max messages per chat in one go
MIN_DELAY = 15.0 # Seconds between message reads
MAX_DELAY = 45.0
CHAT_TRANSITION_DELAY = (2, 5) # Minutes
SLEEP_WINDOW = (1, 7) # 1 AM to 7 AM - Ghost Mode Sleep

state = StateManager()

def is_luhn_valid(number):
    """Standard Luhn MOD-10 algorithm."""
    digits = [int(d) for d in str(number)]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

def is_night_mode():
    current_hour = datetime.now().hour
    return SLEEP_WINDOW[0] <= current_hour < SLEEP_WINDOW[1]

async def human_delay(min_s=MIN_DELAY, max_s=MAX_DELAY):
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)

async def collect_ghost_mode():
    print("--- [ Project SCYTHE: GHOST MODE ACTIVE ] ---")
    
    if is_night_mode():
        print("Night Mode Active. The Ghost is dormant. Mission paused.")
        return

    if not API_ID or not API_HASH:
        print("Error: API_ID or API_HASH missing in config.env")
        return

    client = TelegramClient('shadow_session', API_ID, API_HASH)
    await client.start(phone=PHONE_NUMBER)
    print("Authentication Layer: SECURE.")

    cards_found = []
    dialogs_processed = 0

    # Get all dialogs with unread messages
    all_target_dialogs = []
    async for dialog in client.iter_dialogs():
        if dialog.unread_count > 0:
            all_target_dialogs.append(dialog)

    if not all_target_dialogs:
        print("Radar Clean: No unread intelligence detected.")
        await client.disconnect()
        return

    # Shuffle for randomness
    random.shuffle(all_target_dialogs)
    target_subset = all_target_dialogs[:BATCH_CHAT_LIMIT]

    print(f"Intelligence Sector: Selected {len(target_subset)} targets for scrubbing.")

    for dialog in target_subset:
        last_id = state.get_last_id(dialog.id)
        print(f"Scrubbing: {dialog.name} (Continuing from ID: {last_id})")
        
        processed_in_dialog = 0
        current_max_id = last_id
        
        # Iter_messages from last_id onwards
        async for msg in client.iter_messages(dialog.id, min_id=last_id, limit=MESSAGE_PROCESS_LIMIT):
            processed_in_dialog += 1
            if msg.id > current_max_id:
                current_max_id = msg.id
            
            if msg.text:
                matches = re.findall(CARD_REGEX, msg.text)
                if matches:
                    for card in matches:
                        parts = card.split('|')
                        if len(parts) >= 3:
                            card_num = parts[0].strip()
                            if not is_luhn_valid(card_num): continue
                            
                            # Normalization
                            year = parts[2].strip()
                            if len(year) == 2: parts[2] = "20" + year
                            
                            # CVV Injection if missing
                            if len(parts) < 4 or not parts[3].strip():
                                injected_cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
                                if len(parts) < 4: parts.append(injected_cvv)
                                else: parts[3] = injected_cvv
                            
                            # Final Vector
                            card = "|".join([p.strip() for p in parts if p.strip()])
                        
                        cards_found.append(card)
            
            # STEALTH: Micro-delay between messages
            if processed_in_dialog < MESSAGE_PROCESS_LIMIT:
                await human_delay()

        # Update persistence state
        state.update_last_id(dialog.id, current_max_id)
        
        # Randomly decide to acknowledge read (70% chance to look natural)
        if random.random() > 0.3:
            await client.send_read_acknowledge(dialog.id, max_id=current_max_id)
            print(f"  > [ACK] {dialog.name} synchronized.")
        
        dialogs_processed += 1
        if dialogs_processed < len(target_subset):
            # STEALTH: Long transition between chats
            t_delay = random.uniform(CHAT_TRANSITION_DELAY[0]*60, CHAT_TRANSITION_DELAY[1]*60)
            print(f"  > Transitioning... Idle for {int(t_delay/60)}m {int(t_delay%60)}s")
            await asyncio.sleep(t_delay)

    # Save to staging
    if cards_found:
        unique_cards = list(dict.fromkeys(cards_found))
        state.stage_cards(unique_cards)
        print(f"Intelligence Staged: {len(unique_cards)} new vectors stored.")
    
    print("Mission Phase Complete. Retiring to shadows.")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(collect_ghost_mode())
