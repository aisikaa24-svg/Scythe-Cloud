import re

# The new regex from the collector files
CARD_REGEX = r'(\d{14,16})(?:[\s/|:-]+)(\d{1,2})(?:[\s/|:-]+)(\d{2,4})(?:(?:[\s/|:-]+)(\d{3,4}))?'

test_strings = [
    "1234567812345678|12|2025|123",
    "4444555566667777/01/24/999",
    "5555666677778888 05 2026 111",
    "4000111122223333:10:25",
    "5111222233334444-11-2027-444",
    "Random text 4999888877776666|08|2024|000 some more text",
    "Multiple cards: 4111222233334444/12/2025/111 and 5222333344445555 10 26 222"
]

def test_extraction():
    print("--- Testing SCYTHE Extraction Layer ---")
    for s in test_strings:
        print(f"\nProcessing: {s}")
        matches = re.findall(CARD_REGEX, s)
        for groups in matches:
            num = groups[0]
            month = groups[1]
            year = groups[2]
            cvv = groups[3] if len(groups) > 3 and groups[3] else "N/A"
            print(f"  > FOUND: CC: {num} | MM: {month} | YY: {year} | CVV: {cvv}")

if __name__ == "__main__":
    test_extraction()
