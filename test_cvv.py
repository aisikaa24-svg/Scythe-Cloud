import re
import random

CARD_REGEX = r'(\d{14,16}\|\d{1,2}\|\d{2,4}(?:\|\d{3,4})?\|?)'

def test_injection(text):
    matches = re.findall(CARD_REGEX, text)
    results = []
    for card in matches:
        parts = card.split('|')
        if len(parts) >= 3:
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
        results.append(card)
    return results

# Test cases
test_cases = [
    "4539123456781234|12|25",        # Missing CVV
    "5105105105105105|01|2028|",    # Empty CVV after pipe
    "4000123456789012|05|24|123",   # Already has CVV
    "378282246310005|10|30"         # 15 digits (Amex - should still get 3 digits by current logic)
]

for tc in test_cases:
    print(f"Input: {tc}")
    print(f"Output: {test_injection(tc)}")
    print("-" * 20)
