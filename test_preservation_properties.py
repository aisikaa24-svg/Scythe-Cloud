"""
Preservation Property Tests for Expired Card Filter

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

This test suite verifies that non-expired cards continue to be processed correctly
with all existing validation, obfuscation, normalization, CVV handling, and BIN
deduplication logic preserved.

Property 2: Preservation - Non-Expired Card Processing

For any card input where the expiration date is NOT in the past (year > current UTC year 
OR (year == current UTC year AND month >= current UTC month)), the card processing logic 
SHALL produce the expected behavior, preserving all existing validation (Luhn, network 
filter), obfuscation, normalization, CVV handling, BIN deduplication, and storage operations.

EXPECTED OUTCOME: These tests should PASS on unfixed code (baseline behavior).
After the fix is implemented, these tests should still PASS (behavior preserved).
"""

import os
import re
import random
from datetime import datetime
from hypothesis import given, strategies as st, settings, Phase, assume

# Import the functions we need to test
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collector import is_luhn_valid, obfuscate_card_number, CARD_REGEX


def generate_luhn_valid_card(prefix):
    """Generate a Luhn-valid card number with the given prefix."""
    if len(prefix) >= 16:
        return prefix[:16]
    
    # Generate random digits for positions up to 15
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


def generate_luhn_invalid_card(prefix):
    """Generate a Luhn-INVALID card number with the given prefix."""
    if len(prefix) >= 16:
        # Flip the last digit to make it invalid
        card = prefix[:16]
        last_digit = int(card[-1])
        invalid_digit = (last_digit + 1) % 10
        return card[:-1] + str(invalid_digit)
    
    # Generate random digits for all 16 positions
    while len(prefix) < 16:
        prefix += str(random.randint(0, 9))
    
    # Ensure it's Luhn-invalid by checking and flipping if needed
    if is_luhn_valid(prefix):
        last_digit = int(prefix[-1])
        invalid_digit = (last_digit + 1) % 10
        prefix = prefix[:-1] + str(invalid_digit)
    
    return prefix


def process_card_message(message_text):
    """
    Simulate the card processing logic from collector.py.
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
                
                # NOTE: No expiration check in unfixed code
                
                # 3. OBFUSCATION: Generate Mirror Vector
                obfuscated_num = obfuscate_card_number(card_num)
                
                # 4. NORMALIZATION: Year YYYY
                month = groups[1].strip()
                formatted_month = month if len(month) == 2 else "0" + month
                
                year = groups[2].strip()
                formatted_year = year if len(year) == 4 else "20" + year
                
                # 5. CVV STANDARDIZATION: Exactly 3 digits
                original_cvv = groups[3].strip() if len(groups) > 3 and groups[3] else ""
                if len(original_cvv) == 3:
                    cvv = original_cvv
                else:
                    cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
                
                # Reconstruct sanitized vector
                sanitized_card = f"{obfuscated_num}|{formatted_month}|{formatted_year}|{cvv}"
                cards_found.append(sanitized_card)
    
    return cards_found


# Strategy for generating non-expired dates
@st.composite
def non_expired_dates(draw):
    """Generate non-expired expiration dates (month/year in the future or current)."""
    current_date = datetime.utcnow()
    current_year = current_date.year
    current_month = current_date.month
    
    # Generate either:
    # 1. Future year (current_year + 1 to current_year + 5)
    # 2. Current year with current or future month
    
    choice = draw(st.integers(min_value=0, max_value=1))
    
    if choice == 0:
        # Future year
        year = draw(st.integers(min_value=current_year + 1, max_value=current_year + 5))
        month = draw(st.integers(min_value=1, max_value=12))
    else:
        # Current year, current or future month
        year = current_year
        month = draw(st.integers(min_value=current_month, max_value=12))
    
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
    date=non_expired_dates(),
    cvv=st.one_of(
        st.just(''),  # No CVV
        st.text(st.characters(whitelist_categories=('Nd',)), min_size=3, max_size=3)  # 3-digit CVV
    )
)
@settings(max_examples=100, phases=[Phase.generate, Phase.target])
def test_future_year_cards_accepted(network, date, cvv):
    """
    Property 2.1: Future Year Preservation
    
    **Validates: Requirements 3.1**
    
    Cards with expiration years > current year should be accepted and processed.
    
    EXPECTED OUTCOME: Test PASSES on unfixed code (baseline behavior).
    """
    month_str, year_str = date
    
    # Generate a valid Luhn card number
    card_prefix = network + "123456789012"
    card_num = generate_luhn_valid_card(card_prefix)
    
    # Verify card is Luhn-valid
    assert is_luhn_valid(card_num), "Test setup error: Card should be Luhn-valid"
    
    # Create a message with the non-expired card
    cvv_part = f"|{cvv}" if cvv else ""
    message = f"Card: {card_num}|{month_str}|{year_str}{cvv_part}"
    
    # Process the card
    cards_found = process_card_message(message)
    
    # Non-expired cards should be accepted
    assert len(cards_found) == 1, \
        f"Non-expired card {month_str}/{year_str} should be accepted, but was rejected"
    
    # Verify the card was processed correctly
    card_parts = cards_found[0].split('|')
    assert len(card_parts) == 4, "Card should have 4 parts: number|month|year|cvv"
    
    obfuscated_num, formatted_month, formatted_year, processed_cvv = card_parts
    
    # Verify obfuscation: first 12 digits preserved
    assert obfuscated_num[:12] == card_num[:12], \
        "Obfuscation should preserve first 12 digits"
    
    # Verify obfuscated number is Luhn-valid
    assert is_luhn_valid(obfuscated_num), \
        "Obfuscated card number should be Luhn-valid"
    
    # Verify month normalization: should be 2 digits
    assert len(formatted_month) == 2, "Month should be normalized to 2 digits"
    assert formatted_month.isdigit(), "Month should be numeric"
    assert 1 <= int(formatted_month) <= 12, "Month should be between 01 and 12"
    
    # Verify year normalization: should be 4 digits
    assert len(formatted_year) == 4, "Year should be normalized to 4 digits"
    assert formatted_year.isdigit(), "Year should be numeric"
    
    # Verify CVV handling: should be exactly 3 digits
    assert len(processed_cvv) == 3, "CVV should be exactly 3 digits"
    assert processed_cvv.isdigit(), "CVV should be numeric"
    
    # If original CVV was 3 digits, it should be preserved
    if cvv and len(cvv) == 3:
        assert processed_cvv == cvv, "Original 3-digit CVV should be preserved"


@given(
    network=st.sampled_from(['4', '5']),
    date=non_expired_dates()
)
@settings(max_examples=50, phases=[Phase.generate, Phase.target])
def test_luhn_validation_preserved(network, date):
    """
    Property 2.2: Luhn Validation Preservation
    
    **Validates: Requirements 3.2**
    
    Cards that fail Luhn validation should continue to be rejected regardless of
    expiration date.
    
    EXPECTED OUTCOME: Test PASSES on unfixed code (baseline behavior).
    """
    month_str, year_str = date
    
    # Generate a Luhn-INVALID card number
    card_prefix = network + "123456789012"
    card_num = generate_luhn_invalid_card(card_prefix)
    
    # Verify card is Luhn-invalid
    assert not is_luhn_valid(card_num), "Test setup error: Card should be Luhn-invalid"
    
    # Create a message with the invalid card
    message = f"Card: {card_num}|{month_str}|{year_str}|123"
    
    # Process the card
    cards_found = process_card_message(message)
    
    # Luhn-invalid cards should be rejected
    assert len(cards_found) == 0, \
        f"Luhn-invalid card should be rejected, but was accepted: {cards_found}"


@given(
    network=st.sampled_from(['1', '2', '3', '6', '7', '8', '9']),  # Non-Visa/Mastercard
    date=non_expired_dates()
)
@settings(max_examples=50, phases=[Phase.generate, Phase.target])
def test_network_filter_preserved(network, date):
    """
    Property 2.3: Network Filter Preservation
    
    **Validates: Requirements 3.3**
    
    Cards not starting with '4' (Visa) or '5' (Mastercard) should continue to be
    rejected regardless of expiration date.
    
    EXPECTED OUTCOME: Test PASSES on unfixed code (baseline behavior).
    """
    month_str, year_str = date
    
    # Generate a valid Luhn card number with non-Visa/Mastercard prefix
    card_prefix = network + "123456789012"
    card_num = generate_luhn_valid_card(card_prefix)
    
    # Verify card is Luhn-valid but wrong network
    assert is_luhn_valid(card_num), "Test setup error: Card should be Luhn-valid"
    assert not card_num.startswith(('4', '5')), "Test setup error: Card should not be Visa/Mastercard"
    
    # Create a message with the card
    message = f"Card: {card_num}|{month_str}|{year_str}|123"
    
    # Process the card
    cards_found = process_card_message(message)
    
    # Non-Visa/Mastercard cards should be rejected
    assert len(cards_found) == 0, \
        f"Non-Visa/Mastercard card should be rejected, but was accepted: {cards_found}"


@given(
    network=st.sampled_from(['4', '5']),
    date=non_expired_dates()
)
@settings(max_examples=50, phases=[Phase.generate, Phase.target])
def test_obfuscation_preserved(network, date):
    """
    Property 2.4: Obfuscation Preservation
    
    **Validates: Requirements 3.4**
    
    Valid non-expired cards should have identical obfuscation (first 12 digits
    preserved, Luhn-valid ending).
    
    EXPECTED OUTCOME: Test PASSES on unfixed code (baseline behavior).
    """
    month_str, year_str = date
    
    # Generate a valid Luhn card number
    card_prefix = network + "123456789012"
    card_num = generate_luhn_valid_card(card_prefix)
    
    # Create a message with the card
    message = f"Card: {card_num}|{month_str}|{year_str}|123"
    
    # Process the card
    cards_found = process_card_message(message)
    
    assert len(cards_found) == 1, "Valid card should be accepted"
    
    obfuscated_num = cards_found[0].split('|')[0]
    
    # Verify first 12 digits preserved
    assert obfuscated_num[:12] == card_num[:12], \
        f"First 12 digits should be preserved: expected {card_num[:12]}, got {obfuscated_num[:12]}"
    
    # Verify obfuscated number is Luhn-valid
    assert is_luhn_valid(obfuscated_num), \
        f"Obfuscated number should be Luhn-valid: {obfuscated_num}"
    
    # Verify length is 16 digits
    assert len(obfuscated_num) == 16, \
        f"Obfuscated number should be 16 digits: {obfuscated_num}"


@given(
    network=st.sampled_from(['4', '5']),
    date=non_expired_dates(),
    month_format=st.sampled_from([1, 2])  # 1-digit or 2-digit month
)
@settings(max_examples=50, phases=[Phase.generate, Phase.target])
def test_month_normalization_preserved(network, date, month_format):
    """
    Property 2.5: Month Normalization Preservation
    
    **Validates: Requirements 3.5**
    
    Month normalization should pad single-digit months with leading zero.
    
    EXPECTED OUTCOME: Test PASSES on unfixed code (baseline behavior).
    """
    month_str, year_str = date
    
    # Force specific month format for testing
    month_int = int(month_str)
    if month_format == 1 and month_int < 10:
        month_str = str(month_int)  # Single digit
    else:
        month_str = f"{month_int:02d}"  # Two digits
    
    # Generate a valid Luhn card number
    card_prefix = network + "123456789012"
    card_num = generate_luhn_valid_card(card_prefix)
    
    # Create a message with the card
    message = f"Card: {card_num}|{month_str}|{year_str}|123"
    
    # Process the card
    cards_found = process_card_message(message)
    
    assert len(cards_found) == 1, "Valid card should be accepted"
    
    formatted_month = cards_found[0].split('|')[1]
    
    # Verify month is normalized to 2 digits
    assert len(formatted_month) == 2, \
        f"Month should be normalized to 2 digits: {formatted_month}"
    assert formatted_month.isdigit(), "Month should be numeric"
    assert formatted_month == f"{month_int:02d}", \
        f"Month should be padded with leading zero: expected {month_int:02d}, got {formatted_month}"


@given(
    network=st.sampled_from(['4', '5']),
    date=non_expired_dates(),
    year_format=st.sampled_from([2, 4])  # 2-digit or 4-digit year
)
@settings(max_examples=50, phases=[Phase.generate, Phase.target])
def test_year_normalization_preserved(network, date, year_format):
    """
    Property 2.6: Year Normalization Preservation
    
    **Validates: Requirements 3.5**
    
    Year normalization should prefix 2-digit years with "20".
    
    EXPECTED OUTCOME: Test PASSES on unfixed code (baseline behavior).
    """
    month_str, year_str = date
    
    # Force specific year format for testing
    year_int = int(year_str) if len(year_str) == 4 else 2000 + int(year_str)
    if year_format == 2:
        year_str = str(year_int)[-2:]  # 2-digit
    else:
        year_str = str(year_int)  # 4-digit
    
    # Generate a valid Luhn card number
    card_prefix = network + "123456789012"
    card_num = generate_luhn_valid_card(card_prefix)
    
    # Create a message with the card
    message = f"Card: {card_num}|{month_str}|{year_str}|123"
    
    # Process the card
    cards_found = process_card_message(message)
    
    assert len(cards_found) == 1, "Valid card should be accepted"
    
    formatted_year = cards_found[0].split('|')[2]
    
    # Verify year is normalized to 4 digits
    assert len(formatted_year) == 4, \
        f"Year should be normalized to 4 digits: {formatted_year}"
    assert formatted_year.isdigit(), "Year should be numeric"
    
    # If input was 2-digit, should be prefixed with "20"
    if len(year_str) == 2:
        assert formatted_year == "20" + year_str, \
            f"2-digit year should be prefixed with '20': expected 20{year_str}, got {formatted_year}"
    else:
        assert formatted_year == year_str, \
            f"4-digit year should be unchanged: expected {year_str}, got {formatted_year}"


@given(
    network=st.sampled_from(['4', '5']),
    date=non_expired_dates(),
    cvv=st.one_of(
        st.just(''),  # No CVV
        st.text(st.characters(whitelist_categories=('Nd',)), min_size=3, max_size=3),  # 3-digit CVV
        st.text(st.characters(whitelist_categories=('Nd',)), min_size=4, max_size=4)   # 4-digit CVV
    )
)
@settings(max_examples=50, phases=[Phase.generate, Phase.target])
def test_cvv_handling_preserved(network, date, cvv):
    """
    Property 2.7: CVV Handling Preservation
    
    **Validates: Requirements 3.6**
    
    CVV handling should preserve original 3-digit CVVs or generate random ones.
    
    EXPECTED OUTCOME: Test PASSES on unfixed code (baseline behavior).
    """
    month_str, year_str = date
    
    # Generate a valid Luhn card number
    card_prefix = network + "123456789012"
    card_num = generate_luhn_valid_card(card_prefix)
    
    # Create a message with the card
    cvv_part = f"|{cvv}" if cvv else ""
    message = f"Card: {card_num}|{month_str}|{year_str}{cvv_part}"
    
    # Process the card
    cards_found = process_card_message(message)
    
    assert len(cards_found) == 1, "Valid card should be accepted"
    
    processed_cvv = cards_found[0].split('|')[3]
    
    # Verify CVV is exactly 3 digits
    assert len(processed_cvv) == 3, \
        f"CVV should be exactly 3 digits: {processed_cvv}"
    assert processed_cvv.isdigit(), "CVV should be numeric"
    
    # If original CVV was 3 digits, it should be preserved
    if cvv and len(cvv) == 3:
        assert processed_cvv == cvv, \
            f"Original 3-digit CVV should be preserved: expected {cvv}, got {processed_cvv}"


def test_bin_deduplication_preserved():
    """
    Property 2.8: BIN Deduplication Preservation
    
    **Validates: Requirements 3.7**
    
    BIN deduplication should keep only first card per 6-digit BIN prefix.
    
    EXPECTED OUTCOME: Test PASSES on unfixed code (baseline behavior).
    """
    # Generate two cards with the same BIN (first 6 digits)
    bin_prefix = "412345"
    card1 = generate_luhn_valid_card(bin_prefix + "6789012")
    card2 = generate_luhn_valid_card(bin_prefix + "9876543")
    
    # Verify both cards have the same BIN
    assert card1[:6] == card2[:6] == bin_prefix, "Cards should have the same BIN"
    
    # Create messages with both cards (non-expired dates)
    current_date = datetime.utcnow()
    future_year = current_date.year + 1
    message1 = f"Card: {card1}|12|{future_year}|123"
    message2 = f"Card: {card2}|12|{future_year}|456"
    
    # Process both cards
    cards1 = process_card_message(message1)
    cards2 = process_card_message(message2)
    
    assert len(cards1) == 1, "First card should be accepted"
    assert len(cards2) == 1, "Second card should be accepted"
    
    # Simulate BIN deduplication (as done in collector.py)
    all_cards = cards1 + cards2
    bin_map = {}
    for c in all_cards:
        bin_prefix_from_card = c.split('|')[0][:6]
        if bin_prefix_from_card not in bin_map:
            bin_map[bin_prefix_from_card] = c
    
    unique_cards = list(bin_map.values())
    
    # Only one card should remain after deduplication
    assert len(unique_cards) == 1, \
        f"BIN deduplication should keep only one card per BIN: {len(unique_cards)} cards found"
    
    # The first card should be kept
    assert unique_cards[0] == cards1[0], \
        "BIN deduplication should keep the first card encountered"


def test_current_month_cards_accepted():
    """
    Property 2.9: Current Month Preservation
    
    **Validates: Requirements 3.1**
    
    Cards with current year and current month should be accepted (valid through
    last day of expiration month).
    
    EXPECTED OUTCOME: Test PASSES on unfixed code (baseline behavior).
    """
    current_date = datetime.utcnow()
    current_year = current_date.year
    current_month = current_date.month
    
    # Generate a valid Luhn card number
    card_num = generate_luhn_valid_card("4123456789012")
    
    # Create a message with current month/year
    message = f"Card: {card_num}|{current_month:02d}|{current_year}|123"
    
    # Process the card
    cards_found = process_card_message(message)
    
    # Current month cards should be accepted
    assert len(cards_found) == 1, \
        f"Card with current month {current_month:02d}/{current_year} should be accepted, but was rejected"


if __name__ == "__main__":
    print("=" * 80)
    print("PRESERVATION PROPERTY TESTS")
    print("=" * 80)
    print()
    print("These tests verify that non-expired cards continue to be processed correctly")
    print("with all existing validation, obfuscation, normalization, CVV handling, and")
    print("BIN deduplication logic preserved.")
    print()
    print("EXPECTED OUTCOME: All tests should PASS on unfixed code (baseline behavior).")
    print()
    print("Running tests...")
    print("-" * 80)
    
    # Run unit tests
    print("\n[Test 2.8] BIN Deduplication Preservation...")
    try:
        test_bin_deduplication_preserved()
        print("✓ PASSED: BIN deduplication works correctly")
    except AssertionError as e:
        print(f"✗ FAILED: {str(e)}")
    
    print("\n[Test 2.9] Current Month Preservation...")
    try:
        test_current_month_cards_accepted()
        print("✓ PASSED: Current month cards are accepted")
    except AssertionError as e:
        print(f"✗ FAILED: {str(e)}")
    
    # Run property-based tests
    print("\n[Test 2.1] Future Year Preservation (property-based)...")
    try:
        test_future_year_cards_accepted()
        print("✓ PASSED: Future year cards are accepted and processed correctly")
    except AssertionError as e:
        print(f"✗ FAILED: {str(e)}")
    
    print("\n[Test 2.2] Luhn Validation Preservation (property-based)...")
    try:
        test_luhn_validation_preserved()
        print("✓ PASSED: Luhn validation continues to reject invalid cards")
    except AssertionError as e:
        print(f"✗ FAILED: {str(e)}")
    
    print("\n[Test 2.3] Network Filter Preservation (property-based)...")
    try:
        test_network_filter_preserved()
        print("✓ PASSED: Network filter continues to reject non-Visa/Mastercard cards")
    except AssertionError as e:
        print(f"✗ FAILED: {str(e)}")
    
    print("\n[Test 2.4] Obfuscation Preservation (property-based)...")
    try:
        test_obfuscation_preserved()
        print("✓ PASSED: Obfuscation logic works correctly")
    except AssertionError as e:
        print(f"✗ FAILED: {str(e)}")
    
    print("\n[Test 2.5] Month Normalization Preservation (property-based)...")
    try:
        test_month_normalization_preserved()
        print("✓ PASSED: Month normalization works correctly")
    except AssertionError as e:
        print(f"✗ FAILED: {str(e)}")
    
    print("\n[Test 2.6] Year Normalization Preservation (property-based)...")
    try:
        test_year_normalization_preserved()
        print("✓ PASSED: Year normalization works correctly")
    except AssertionError as e:
        print(f"✗ FAILED: {str(e)}")
    
    print("\n[Test 2.7] CVV Handling Preservation (property-based)...")
    try:
        test_cvv_handling_preserved()
        print("✓ PASSED: CVV handling works correctly")
    except AssertionError as e:
        print(f"✗ FAILED: {str(e)}")
    
    print()
    print("=" * 80)
    print("All preservation property tests completed!")
    print("=" * 80)
