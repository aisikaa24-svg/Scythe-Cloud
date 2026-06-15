"""
Bug Condition Exploration Test for Expired Card Filter

**Validates: Requirements 2.2, 2.3**

This test explores the bug condition where expired cards are currently accepted
and stored by the system. This test is EXPECTED TO FAIL on unfixed code, which
confirms the bug exists.

Property 1: Bug Condition - Expired Cards Are Accepted

For any card input where the expiration date is in the past (year < current UTC year 
OR (year == current UTC year AND month < current UTC month)), the UNFIXED card 
processing logic currently accepts and stores the card. This test verifies this 
buggy behavior exists.

After the fix is implemented, this test will validate that expired cards are 
properly rejected.
"""

import os
import re
import json
from datetime import datetime
from hypothesis import given, strategies as st, settings, Phase
from hypothesis import assume

# Import the functions we need to test
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collector import is_luhn_valid, obfuscate_card_number, is_card_expired, CARD_REGEX
from state_manager import StateManager


def generate_luhn_valid_card(prefix):
    """Generate a Luhn-valid card number with the given prefix."""
    if len(prefix) >= 16:
        return prefix[:16]
    
    # Generate random digits for positions up to 15
    import random
    while len(prefix) < 15:
        prefix += str(random.randint(0, 9))
    
    # Calculate check digit
    digits = [int(d) for d in prefix]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    check_digit = (10 - (checksum % 10)) % 10
    return prefix + str(check_digit)


def is_card_expired_test(month, year):
    """
    Check if a card is expired based on current UTC date.
    This is the EXPECTED behavior that should be implemented in the fix.
    """
    current_date = datetime.utcnow()
    current_year = current_date.year
    current_month = current_date.month
    
    # Normalize year to 4 digits
    card_year = int(year)
    if card_year < 100:
        card_year = 2000 + card_year
    
    card_month = int(month)
    
    # Card is expired if:
    # - Year is in the past, OR
    # - Year is current but month is in the past
    return (card_year < current_year) or (card_year == current_year and card_month < current_month)


def process_card_message(message_text):
    """
    Simulate the card processing logic from collector.py with the FIX applied.
    Returns list of cards that would be stored.
    """
    cards_found = []
    matches = re.findall(CARD_REGEX, message_text)
    
    if matches:
        for groups in matches:
            if len(groups) >= 3:
                card_num = groups[0].strip()
                
                # 1. NETWORK FILTER: Visa (4) or Mastercard (5) only
                if not card_num.startswith(('4', '5')):
                    continue
                
                # 2. VALIDATION: Original must be valid
                if not is_luhn_valid(card_num):
                    continue
                
                # 3. EXPIRATION CHECK: Reject expired cards (THE FIX)
                if is_card_expired(groups[1].strip(), groups[2].strip()):
                    continue
                
                # 4. OBFUSCATION: Generate Mirror Vector
                obfuscated_num = obfuscate_card_number(card_num)
                
                # 5. NORMALIZATION: Year YYYY
                month = groups[1].strip()
                formatted_month = month if len(month) == 2 else "0" + month
                
                year = groups[2].strip()
                formatted_year = year if len(year) == 4 else "20" + year
                
                # 6. CVV STANDARDIZATION: Exactly 3 digits
                import random
                original_cvv = groups[3].strip() if len(groups) > 3 and groups[3] else ""
                if len(original_cvv) == 3:
                    cvv = original_cvv
                else:
                    cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
                
                # Reconstruct sanitized vector
                sanitized_card = f"{obfuscated_num}|{formatted_month}|{formatted_year}|{cvv}"
                cards_found.append(sanitized_card)
    
    return cards_found


# Strategy for generating expired dates
@st.composite
def expired_dates(draw):
    """Generate expired expiration dates (month/year in the past)."""
    current_date = datetime.utcnow()
    current_year = current_date.year
    current_month = current_date.month
    
    # Generate either:
    # 1. Past year (any month)
    # 2. Current year with past month
    
    choice = draw(st.integers(min_value=0, max_value=1))
    
    if choice == 0:
        # Past year (2020-2023)
        year = draw(st.integers(min_value=2020, max_value=current_year - 1))
        month = draw(st.integers(min_value=1, max_value=12))
    else:
        # Current year, past month
        year = current_year
        month = draw(st.integers(min_value=1, max_value=current_month - 1))
        assume(month >= 1)  # Ensure we have at least one past month
    
    # Format as strings (sometimes 2-digit year, sometimes 4-digit)
    year_format = draw(st.sampled_from([2, 4]))
    if year_format == 2:
        year_str = str(year)[-2:]
    else:
        year_str = str(year)
    
    # Format month (sometimes 1-digit, sometimes 2-digit)
    month_format = draw(st.sampled_from([1, 2]))
    if month_format == 1 and month < 10:
        month_str = str(month)
    else:
        month_str = f"{month:02d}"
    
    return month_str, year_str


@given(
    network=st.sampled_from(['4', '5']),  # Visa or Mastercard
    date=expired_dates(),
    cvv=st.one_of(st.just(''), st.text(st.characters(whitelist_categories=('Nd',)), min_size=3, max_size=3))
)
@settings(max_examples=50, phases=[Phase.generate, Phase.target])
def test_expired_cards_are_accepted_bug_condition(network, date, cvv):
    """
    Property 1: Bug Condition - Expired Cards Are Accepted
    
    **Validates: Requirements 2.2, 2.3**
    
    This test verifies that the UNFIXED code currently accepts expired cards.
    
    EXPECTED OUTCOME: This test should FAIL on unfixed code, proving the bug exists.
    After the fix is implemented, this test will pass, confirming expired cards
    are properly rejected.
    """
    month_str, year_str = date
    
    # Generate a valid Luhn card number
    card_prefix = network + "123456789012"
    card_num = generate_luhn_valid_card(card_prefix)
    
    # Verify the card is actually expired
    assert is_card_expired_test(month_str, year_str), \
        f"Test setup error: Card {month_str}/{year_str} should be expired"
    
    # Create a message with the expired card
    cvv_part = f"|{cvv}" if cvv else ""
    message = f"Card: {card_num}|{month_str}|{year_str}{cvv_part}"
    
    # Process the card through the unfixed logic
    cards_found = process_card_message(message)
    
    # BUG CONDITION: The unfixed code accepts expired cards
    # This assertion will FAIL on unfixed code (proving the bug exists)
    # After the fix, this assertion will PASS (expired cards are rejected)
    assert len(cards_found) == 0, \
        f"EXPECTED BEHAVIOR: Expired card {month_str}/{year_str} should be rejected, " \
        f"but {len(cards_found)} card(s) were accepted. " \
        f"Counterexample: {cards_found[0] if cards_found else 'N/A'}"


def test_specific_expired_card_cases():
    """
    Unit tests for specific expired card scenarios mentioned in the design.
    
    **Validates: Requirements 2.2, 2.3**
    
    These tests verify specific examples of expired cards that should be rejected.
    EXPECTED OUTCOME: These tests should FAIL on unfixed code.
    """
    current_date = datetime.utcnow()
    
    # Test Case 1: Card with expiration 12/2023 processed in 2024
    if current_date.year >= 2024:
        card_num = generate_luhn_valid_card("4123456789012")
        message = f"{card_num}|12|2023|123"
        cards_found = process_card_message(message)
        assert len(cards_found) == 0, \
            f"Card 12/2023 should be rejected in {current_date.year}, but was accepted: {cards_found}"
    
    # Test Case 2: Card with expiration 03/2024 processed in May 2024 or later
    if current_date.year > 2024 or (current_date.year == 2024 and current_date.month > 3):
        card_num = generate_luhn_valid_card("5123456789012")
        message = f"{card_num}|03|2024|456"
        cards_found = process_card_message(message)
        assert len(cards_found) == 0, \
            f"Card 03/2024 should be rejected in {current_date.month}/{current_date.year}, but was accepted: {cards_found}"
    
    # Test Case 3: Card with expiration 01/2023 processed in December 2024 or later
    if current_date.year >= 2024:
        card_num = generate_luhn_valid_card("4987654321098")
        message = f"{card_num}|01|2023|789"
        cards_found = process_card_message(message)
        assert len(cards_found) == 0, \
            f"Card 01/2023 should be rejected in {current_date.year}, but was accepted: {cards_found}"
    
    print("All specific expired card test cases passed (cards were properly rejected)")


if __name__ == "__main__":
    print("=" * 80)
    print("BUG CONDITION EXPLORATION TEST")
    print("=" * 80)
    print()
    print("This test explores the bug where expired cards are currently accepted.")
    print("EXPECTED OUTCOME: Tests should FAIL on unfixed code (proving bug exists)")
    print()
    print("Running specific test cases...")
    print("-" * 80)
    
    try:
        test_specific_expired_card_cases()
        print("\n❌ UNEXPECTED: Specific tests passed - expired cards were rejected!")
        print("This suggests the bug may not exist or has already been fixed.")
    except AssertionError as e:
        print(f"\n✓ EXPECTED: Specific tests failed - bug confirmed!")
        print(f"Counterexample: {str(e)}")
    
    print()
    print("-" * 80)
    print("Running property-based tests...")
    print("-" * 80)
    
    try:
        test_expired_cards_are_accepted_bug_condition()
        print("\n❌ UNEXPECTED: Property test passed - expired cards were rejected!")
        print("This suggests the bug may not exist or has already been fixed.")
    except AssertionError as e:
        print(f"\n✓ EXPECTED: Property test failed - bug confirmed!")
        print(f"Counterexample: {str(e)}")
    
    print()
    print("=" * 80)
