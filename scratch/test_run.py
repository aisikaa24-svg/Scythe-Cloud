import sys
import os
import re
import asyncio
import random

# Fix import paths for modules in the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient, events
from dotenv import load_dotenv
from state_manager import StateManager
from datetime import datetime

# Load configuration from config.env (THE CORRECT ACCOUNT)
load_dotenv('config.env')

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# Regex for card patterns
CARD_REGEX = r'(\d{14,16}\|\d{1,2}\|\d{2,4}(?:\|\d{3,4})?\|?)'

# --- IRON-CLAD STEALTH (EXTRA SAFE) ---
MESSAGE_PROCESS_LIMIT = 300 # Reduced to stay under the radar
MIN_DELAY = 1.5 
MAX_DELAY = 6.0
CHAT_TRANSITION_DELAY = (60, 180) # 1-3 minutes between channels

state = StateManager()

def is_luhn_valid(number):
    try:
        digits = [int(d) for d in str(number)]
        checksum = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            if i % 2 == 1:
                d *= 2
                if d > 9: d -= 9
            checksum += d
        return checksum % 10 == 0
    except: return False

def obfuscate_card_number(original):
    """
    Takes original 16-digit card, keeps first 12 digits,
    generates a random valid Luhn-compliant ending.
    """
    if len(original) < 13: return original # Too short to obfuscate safely
    
    # 1. Take first 12 digits
    base = original[:12]
    
    # 2. Add 3 random digits
    mid = "".join([str(random.randint(0, 9)) for _ in range(3)])
    prefix = base + mid
    
    # 3. Calculate 16th digit (Luhn)
    digits = [int(d) for d in prefix]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 0: # This is the "odd" position from the right (1st, 3rd, etc.)
            d *= 2
            if d > 9: d -= 9
        checksum += d
    
    check_digit = (10 - (checksum % 10)) % 10
    return prefix + str(check_digit)

async def collect_test():
    print("\n" + "="*50)
    print("      SCYTHE: CATCH-UP MISSION INITIALIZED")
    print("="*50)

    if not API_ID or not API_HASH:
        print("❌ Error: API_ID or API_HASH missing in config.env")
        return

    # Force a local user session
    print(f"📡 Initializing session for: {PHONE_NUMBER}")
    client = TelegramClient('scythe_user_session', API_ID, API_HASH)
    
    # Start will prompt for phone/code if not logged in
    await client.start(phone=PHONE_NUMBER)
    
    me = await client.get_me()
    print(f"✅ Authenticated as: {me.first_name} (@{me.username})")

    all_dialogs = []
    print("📡 Scanning for unread intelligence...")
    async for dialog in client.iter_dialogs():
        if dialog.unread_count > 0:
            all_dialogs.append(dialog)

    if not all_dialogs:
        print("📭 Radar Clean: No unread messages found.")
        await client.disconnect()
        return

    print(f"🎯 Total Targets Located: {len(all_dialogs)}")
    print("-" * 50)

    total_cards = []

    for dialog in all_dialogs:
        print(f"\n🔎 ENTERING: {dialog.name}")
        print(f"📊 Backlog: {dialog.unread_count} unread messages.")
        
        # We will process up to MESSAGE_PROCESS_LIMIT
        limit = min(dialog.unread_count, MESSAGE_PROCESS_LIMIT)
        print(f"🚀 Processing top {limit} vectors...")
        
        cards_in_chat = 0
        current_max_id = 0
        
        # Fetch messages
        processed = 0
        async for msg in client.iter_messages(dialog.id, limit=limit):
            processed += 1
            if msg.id > current_max_id: current_max_id = msg.id
            
            if msg.text:
                matches = re.findall(CARD_REGEX, msg.text)
                for card_str in matches:
                    parts = card_str.split('|')
                    if len(parts) >= 3:
                        card_num = parts[0].strip()
                        
                        # 1. NETWORK FILTER: Visa (4) or Mastercard (5) only
                        if not card_num.startswith(('4', '5')): continue
                        
                        # 2. VALIDATION: Must pass original luhn first
                        if not is_luhn_valid(card_num): continue
                        
                        # 3. OBFUSCATION: Generate Mirror Vector
                        obfuscated_num = obfuscate_card_number(card_num)
                        
                        # 4. NORMALIZATION: Year YYYY
                        month = parts[1].strip()
                        if len(month) == 1: parts[1] = "0" + month
                        year = parts[2].strip()
                        if len(year) == 2: parts[2] = "20" + year
                        
                        # 5. CVV STANDARDIZATION: Exactly 3 digits
                        # If existing CVV is 4 (Amex) or missing, randomize it to 3
                        # Otherwise keep it if it's 3
                        original_cvv = parts[3].strip() if len(parts) > 3 else ""
                        if len(original_cvv) == 3:
                            cvv = original_cvv
                        else:
                            cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
                        
                        # Reconstruct sanitized vector
                        sanitized_card = f"{obfuscated_num}|{parts[1]}|{parts[2]}|{cvv}"
                        total_cards.append(sanitized_card)
                        cards_in_chat += 1
            
            if processed % 50 == 0:
                print(f"  > Scanned {processed}/{limit}...")
                await asyncio.sleep(1)

        # Mark as read (Wrapped for stability)
        try:
            await client.send_read_acknowledge(dialog.id, max_id=current_max_id)
            print(f"✅ Sync Complete: {cards_in_chat} vectors extracted.")
            print(f"🧹 Channel {dialog.name} cleared and marked as read.")
        except Exception as e:
            print(f"⚠️ Could not mark {dialog.name} as read (Flood limit/Restriction): {e}")
            print(f"✅ Sync Complete: {cards_in_chat} vectors extracted (Unread count remains).")

        # Transition
        if dialog != all_dialogs[-1]:
            wait = random.uniform(CHAT_TRANSITION_DELAY[0], CHAT_TRANSITION_DELAY[1])
            print(f"⏳ Cooling down for {int(wait)}s before next target...")
            await asyncio.sleep(wait)

    # Final Save
    if total_cards:
        unique = list(dict.fromkeys(total_cards))
        with open('extracted_cards.txt', 'a') as f:
            for c in unique:
                f.write(c + '\n')
        print("\n" + "="*50)
        print(f"💰 MISSION SUCCESS: {len(unique)} unique vectors captured.")
        print(f"📁 Data saved to: extracted_cards.txt")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("📉 MISSION END: No valid vectors found in this sweep.")
        print("="*50)

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(collect_test())
