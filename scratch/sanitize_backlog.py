import os
import random

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

file_path = 'c:/Users/Administrator/Desktop/auto clime/4/extracted_cards.txt'

if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    sanitized_lines = []
    for line in lines:
        parts = line.strip().split('|')
        if len(parts) >= 3:
            card_num = parts[0].strip()
            
            # 1. NETWORK FILTER: Visa (4) or Mastercard (5) only
            if not card_num.startswith(('4', '5')): continue
            
            # 2. OBFUSCATION
            obfuscated_num = obfuscate_card_number(card_num)
            
            # 3. NORMALIZATION: Year YYYY
            month = parts[1].strip()
            if len(month) == 1: month = "0" + month
            year = parts[2].strip()
            if len(year) == 2: year = "20" + year
            
            # 4. CVV STANDARDIZATION: 3 digits
            original_cvv = parts[3].strip() if len(parts) > 3 else ""
            if len(original_cvv) == 3:
                cvv = original_cvv
            else:
                cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
            
            sanitized_lines.append(f"{obfuscated_num}|{month}|{year}|{cvv}")
            
    # Deduplicate
    unique_lines = list(dict.fromkeys(sanitized_lines))
    
    with open(file_path, 'w') as f:
        for line in unique_lines:
            f.write(line + '\n')
    
    print(f"SUCCESS: Sanitzed {len(lines)} original vectors. {len(unique_lines)} Mirror Vectors stored.")
else:
    print("File not found.")
