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
MESSAGE_PROCESS_LIMIT = 500 # High throughput for backlog catch-up
MIN_DELAY = 1.0 # Faster local processing jitter
MAX_DELAY = 5.0
CHAT_TRANSITION_DELAY = (10, 30) # Seconds (shortened for testing, but still safe)
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

def obfuscate_card_number(original):
    """
    Takes original 16-digit card, keeps first 12 digits,
    generates a random valid Luhn-compliant ending.
    """
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

def is_night_mode():
    current_hour = datetime.now().hour
    return SLEEP_WINDOW[0] <= current_hour < SLEEP_WINDOW[1]

async def human_delay(min_s=MIN_DELAY, max_s=MAX_DELAY):
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)

async def collect_ghost_mode():
    print("--- [ Project SCYTHE: HIGH-VOLUME LOCAL MODE ] ---")
    
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

    print(f"Intelligence Sector: Found {len(all_target_dialogs)} targets with unread intel.")

    for dialog in all_target_dialogs:
        last_id = state.get_last_id(dialog.id)
        unread_to_process = min(dialog.unread_count, MESSAGE_PROCESS_LIMIT)
        print(f"Scrubbing: {dialog.name} ({unread_to_process} messages)")
        
        processed_in_dialog = 0
        current_max_id = last_id
        
        # Iter_messages from newest to oldest (default) 
        async for msg in client.iter_messages(dialog.id, limit=unread_to_process):
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
                            
                            # 1. NETWORK FILTER: Visa (4) or Mastercard (5) only
                            if not card_num.startswith(('4', '5')): continue
                            
                            # 2. VALIDATION: Original must be valid
                            if not is_luhn_valid(card_num): continue
                            
                            # 3. OBFUSCATION: Generate Mirror Vector
                            obfuscated_num = obfuscate_card_number(card_num)
                            
                            # 4. NORMALIZATION: Year YYYY
                            month = parts[1].strip()
                            if len(month) == 1: parts[1] = "0" + month
                            year = parts[2].strip()
                            if len(year) == 2: parts[2] = "20" + year
                            
                            # 5. CVV STANDARDIZATION: Exactly 3 digits
                            original_cvv = parts[3].strip() if len(parts) > 3 else ""
                            if len(original_cvv) == 3:
                                cvv = original_cvv
                            else:
                                cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
                            
                            # Reconstruct sanitized vector
                            sanitized_card = f"{obfuscated_num}|{parts[1]}|{parts[2]}|{cvv}"
                        
                        cards_found.append(sanitized_card)
            
            # STEALTH: Micro-delay between batches of messages (optimized)
            if processed_in_dialog % 10 == 0:
                await human_delay(0.5, 1.5)

        # Update persistence state
        state.update_last_id(dialog.id, current_max_id)
        
        # Mark as read to clear the count (Wrapped in try-except for stability)
        try:
            await client.send_read_acknowledge(dialog.id, max_id=current_max_id)
            print(f"  > [DONE] {dialog.name} synchronized and marked as read.")
        except Exception as e:
            print(f"  > [WARN] Could not mark {dialog.name} as read: {e}")
            # Continue mission even if read acknowledge fails
        
        dialogs_processed += 1
        if dialogs_processed < len(all_target_dialogs):
            # Safe transition between chats
            t_delay = random.uniform(CHAT_TRANSITION_DELAY[0], CHAT_TRANSITION_DELAY[1])
            print(f"  > Next target in {int(t_delay)}s...")
            await asyncio.sleep(t_delay)

    # Save to staging
    if cards_found:
        unique_cards = list(dict.fromkeys(cards_found))
        state.stage_cards(unique_cards)
        # Also write to file for immediate visibility
        with open('extracted_cards.txt', 'a') as f:
            for c in unique_cards:
                f.write(c + '\n')
        print(f"Intelligence Staged: {len(unique_cards)} new vectors stored in extracted_cards.txt.")
    
    print("Mission Phase Complete. Final Results Stored.")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(collect_ghost_mode())

if __name__ == '__main__':
    asyncio.run(collect_ghost_mode())
