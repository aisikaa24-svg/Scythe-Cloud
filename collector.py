import os
import re
import asyncio
import random
from telethon import TelegramClient, events
from dotenv import load_dotenv

# Load configuration from config.env
load_dotenv('config.env')

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# Regex for card patterns (Number|Month|Year|Optional_CVV|Optional_Pipe)
# Designed for peak extraction: 14-16 digits followed by pipes and separators.
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

async def collect_and_clean():
    print("--- [ Project SCYTHE: Telegram Card Extractor ] ---")
    
    if not API_ID or not API_HASH:
        print("Error: API_ID or API_HASH missing in config.env")
        return

    client = TelegramClient('shadow_session', API_ID, API_HASH)
    
    await client.start(phone=PHONE_NUMBER)
    print("Authenticated successfully.")

    extracted_count = 0
    total_unread_messages = 0
    cards_found = []

    print("Scanning dialogs for unread content...")
    
    async for dialog in client.iter_dialogs():
        if dialog.unread_count > 0:
            count = dialog.unread_count
            print(f"Scrubbing: {dialog.name} ({count} unread)")
            
            processed_in_dialog = 0
            max_id = 0
            
            # Use iter_messages for memory efficiency and progress tracking
            async for msg in client.iter_messages(dialog.id, limit=count):
                processed_in_dialog += 1
                if msg.id > max_id:
                    max_id = msg.id
                
                if msg.text:
                    # Extract cards using regex
                    matches = re.findall(CARD_REGEX, msg.text)
                    if matches:
                        for card in matches:
                            # Normalize and inject data
                            parts = card.split('|')
                            if len(parts) >= 3:
                                card_num = parts[0].strip()
                                
                                # Basic normalization (consistent with cloud mission)
                                if not is_luhn_valid(card_num):
                                    continue
                                
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
                                
                                # Save cleaned vector
                                card = "|".join([p.strip() for p in parts if p.strip()])
                            
                            cards_found.append(card)
                            extracted_count += 1
                
                # Progress logging every 500 messages
                if processed_in_dialog % 500 == 0:
                    print(f"  > Progress: {processed_in_dialog}/{count} messages processed...")

            total_unread_messages += processed_in_dialog
            
            # Mark all messages in this dialog as read (Mandatory Clean-up)
            if max_id:
                await client.send_read_acknowledge(dialog.id, max_id=max_id)
            print(f"  > [DONE] {dialog.name} synchronized.")

    # Save results to file
    if cards_found:
        # Deduplicate while preserving order
        unique_cards = list(dict.fromkeys(cards_found))
        with open('extracted_cards.txt', 'a', encoding='utf-8') as f:
            for card in unique_cards:
                f.write(f"{card}\n")
        print(f"Success: {len(unique_cards)} unique cards extracted and stored in 'extracted_cards.txt'.")
    else:
        print("No cards found in current unread messages.")

    print(f"Mission Complete: {total_unread_messages} messages synchronized to 'Read' status.")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(collect_and_clean())
