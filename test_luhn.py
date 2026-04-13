import random

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
        mid_suffix = "".join([str(random.randint(0, 9)) for _ in range(suffix_len - 1)])
        candidate_prefix = prefix + mid_suffix
        
        digits = [int(d) for d in candidate_prefix]
        total_sum = 0
        for i, d in enumerate(reversed(digits)):
            # Distances from right: check_digit(1), digits[0](2), digits[1](3)...
            # Even distances (2, 4, 6...) double.
            # Local candidates: digits[0] is at distance 2. Index 0 in reversed(digits) is distance 2.
            if i % 2 == 0:
                d *= 2
                if d > 9: d -= 9
            total_sum += d
        
        check_digit = (10 - (total_sum % 10)) % 10
        return candidate_prefix + str(check_digit)

# TEST CASE: Visa (4), MasterCard (5), and Other (3 - Amex)
test_vectors = [
    "4432526534241991", # Visa (Valid)
    "5105105105105100", # MasterCard (Valid - Generated for test)
    "378282246310005"   # Amex (Should be skipped)
]

for test_card in test_vectors:
    print(f"\nScanning Vector: {test_card}")
    
    # Logic from collector_cloud.py:
    if not (test_card.startswith('4') or test_card.startswith('5')):
        print(f"FAILED: Discarding non-Visa/MC vector.")
        continue
        
    if not is_luhn_valid(test_card):
        print(f"FAILED: Discarding invalid vector.")
        continue

    print(f"SUCCESS: Processing {test_card}...")
    prefix = test_card[:-4]
    extrap = generate_luhn_valid_extrap(prefix, len(test_card))
    print(f"Resulting Extrap: {extrap} | Valid: {is_luhn_valid(extrap)}")
