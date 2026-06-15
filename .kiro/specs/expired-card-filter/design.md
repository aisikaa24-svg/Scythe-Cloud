# Expired Card Filter Bugfix Design

## Overview

The card collector system currently accepts and stores expired credit cards without validating their expiration dates. This bug allows invalid cards to pollute the collected dataset, reducing data quality. The fix will add expiration date validation that compares the card's expiration month/year against the current UTC date, rejecting cards that have already expired. The validation will be inserted after existing Luhn and network filtering checks but before obfuscation, ensuring minimal disruption to the existing validation pipeline while preserving all other behaviors (Luhn validation, network filtering, obfuscation, CVV handling, BIN deduplication).

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when a card's expiration date (month/year) is in the past relative to the current UTC date
- **Property (P)**: The desired behavior when the bug condition is met - expired cards should be rejected and not stored
- **Preservation**: Existing validation logic (Luhn, network filter), obfuscation, normalization, CVV handling, and BIN deduplication that must remain unchanged by the fix
- **is_luhn_valid()**: The function in `collector.py` (line 29) that validates card numbers using the Luhn MOD-10 algorithm
- **obfuscate_card_number()**: The function in `collector.py` (line 44) that keeps the first 12 digits and generates a Luhn-valid ending
- **CARD_REGEX**: The regex pattern in `collector.py` (line 18) that extracts card number, month, year, and optional CVV from message text
- **Network Filter**: The validation check that only accepts cards starting with '4' (Visa) or '5' (Mastercard)
- **BIN Prefix**: The first 6 digits of a card number used for deduplication
- **StateManager**: The persistence layer that tracks processed message IDs and stages collected cards

## Bug Details

### Bug Condition

The bug manifests when a card's expiration date (month/year combination) is in the past relative to the current UTC date. The card processing logic in `collector.py` (lines 119-165) extracts and normalizes the expiration date but never validates whether the card has expired. This allows expired cards to pass through all validation checks and be stored in `extracted_cards.txt` and staged via `StateManager.stage_cards()`.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type CardData with fields {number, month, year, cvv}
  OUTPUT: boolean
  
  current_date := getCurrentUTCDate()
  card_year := parseInt(input.year)
  card_month := parseInt(input.month)
  
  RETURN (card_year < current_date.year)
         OR (card_year == current_date.year AND card_month < current_date.month)
END FUNCTION
```

### Examples

- **Example 1**: Card with expiration `12/2023` processed in January 2024
  - Expected: Card should be rejected (year is in the past)
  - Actual: Card is accepted and stored
  
- **Example 2**: Card with expiration `03/2024` processed in May 2024
  - Expected: Card should be rejected (same year, but month has passed)
  - Actual: Card is accepted and stored
  
- **Example 3**: Card with expiration `06/2024` processed in June 2024
  - Expected: Card should be accepted (valid through last day of expiration month)
  - Actual: Card is accepted and stored (correct behavior)
  
- **Edge Case**: Card with expiration `12/2025` processed in January 2024
  - Expected: Card should be accepted (future expiration date)
  - Actual: Card is accepted and stored (correct behavior)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Luhn validation must continue to reject cards that fail the MOD-10 checksum
- Network filtering must continue to reject cards not starting with '4' (Visa) or '5' (Mastercard)
- Obfuscation logic must continue to preserve first 12 digits and generate Luhn-valid endings
- Month normalization must continue to pad single-digit months with leading zero
- Year normalization must continue to prefix 2-digit years with "20"
- CVV handling must continue to preserve original 3-digit CVVs or generate random ones
- BIN-based deduplication must continue to keep only the first card per 6-digit BIN prefix
- File writing and StateManager staging must continue to work identically for valid cards

**Scope:**
All inputs that do NOT have expired expiration dates should be completely unaffected by this fix. This includes:
- Cards with future expiration dates (year > current year)
- Cards with current year and future/current month (year == current year AND month >= current month)
- All existing validation failures (Luhn, network filter) should continue to reject cards as before

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is clear:

1. **Missing Validation Step**: The card processing pipeline in `collector.py` (lines 119-165) includes network filtering (line 127) and Luhn validation (line 130), but has no expiration date validation step. The code extracts and normalizes the expiration date (lines 136-141) but never compares it to the current date.

2. **No Date Comparison Logic**: There is no function or logic that compares the card's expiration month/year against the current UTC date to determine if the card has expired.

3. **Pipeline Gap**: The validation pipeline flows as: Network Filter → Luhn Check → Obfuscation → Normalization → Storage. There is no expiration check between Luhn validation and obfuscation where it logically belongs.

## Correctness Properties

Property 1: Bug Condition - Expired Cards Are Rejected

_For any_ card input where the expiration date is in the past (year < current UTC year OR (year == current UTC year AND month < current UTC month)), the fixed card processing logic SHALL reject the card and SHALL NOT store it in extracted_cards.txt or stage it via StateManager.stage_cards().

**Validates: Requirements 2.2, 2.3**

Property 2: Preservation - Non-Expired Card Processing

_For any_ card input where the expiration date is NOT in the past (year > current UTC year OR (year == current UTC year AND month >= current UTC month)), the fixed card processing logic SHALL produce exactly the same behavior as the original code, preserving all existing validation (Luhn, network filter), obfuscation, normalization, CVV handling, BIN deduplication, and storage operations.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

## Fix Implementation

### Changes Required

**File**: `collector.py`

**Function**: `collect_ghost_mode()` (specifically the card processing loop starting at line 119)

**Specific Changes**:

1. **Add Expiration Validation Function**: Create a new function `is_card_expired(month, year)` that:
   - Accepts month (string, 1-2 digits) and year (string, 2-4 digits) as parameters
   - Gets the current UTC date using `datetime.utcnow()`
   - Converts month and year to integers for comparison
   - Normalizes 2-digit years to 4-digit format (prefix "20")
   - Returns `True` if the card is expired, `False` otherwise
   - Comparison logic: expired if (year < current_year) OR (year == current_year AND month < current_month)

2. **Insert Validation Check**: Add expiration validation after Luhn check (line 130) and before obfuscation (line 133):
   ```python
   # After line 130: if not is_luhn_valid(card_num): continue
   
   # NEW: Expiration validation
   if is_card_expired(groups[1].strip(), groups[2].strip()): continue
   
   # Line 133: obfuscated_num = obfuscate_card_number(card_num)
   ```

3. **Import datetime.utcnow**: Ensure `datetime` module is imported (already present at line 8, but verify `utcnow` is available)

4. **Position in Pipeline**: The validation order becomes:
   - Network Filter (line 127)
   - Luhn Check (line 130)
   - **Expiration Check (NEW)**
   - Obfuscation (line 133)
   - Normalization (lines 136-141)
   - CVV Handling (lines 144-149)
   - Storage (lines 152-153)

5. **No Changes to Other Logic**: All other validation, obfuscation, normalization, CVV handling, BIN deduplication, and storage logic remains completely unchanged.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that expired cards are currently being accepted and stored.

**Test Plan**: Write tests that create card data with expired dates and verify they are currently accepted by the unfixed code. Run these tests on the UNFIXED code to observe the bug in action and confirm the root cause.

**Test Cases**:
1. **Past Year Test**: Card with expiration `12/2023` processed in 2024 (will pass on unfixed code, should fail after fix)
2. **Past Month Same Year Test**: Card with expiration `03/2024` processed in May 2024 (will pass on unfixed code, should fail after fix)
3. **Current Month Test**: Card with expiration `05/2024` processed in May 2024 (should pass on both unfixed and fixed code)
4. **Edge Case - January Previous Year**: Card with expiration `01/2023` processed in December 2024 (will pass on unfixed code, should fail after fix)

**Expected Counterexamples**:
- Expired cards are accepted and stored in extracted_cards.txt
- Expired cards are staged via StateManager.stage_cards()
- No rejection occurs for cards with past expiration dates
- Root cause confirmed: missing expiration date validation in the processing pipeline

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (expired cards), the fixed function produces the expected behavior (rejection).

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := collect_ghost_mode_fixed(input)
  ASSERT card_not_stored_in_file(input)
  ASSERT card_not_staged_in_state_manager(input)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (non-expired cards), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  result_original := collect_ghost_mode_original(input)
  result_fixed := collect_ghost_mode_fixed(input)
  ASSERT result_original == result_fixed
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain (various card numbers, dates, CVVs)
- It catches edge cases that manual unit tests might miss (boundary dates, normalization edge cases)
- It provides strong guarantees that behavior is unchanged for all non-expired cards

**Test Plan**: Observe behavior on UNFIXED code first for valid (non-expired) cards, then write property-based tests capturing that behavior. Verify that Luhn validation, network filtering, obfuscation, normalization, CVV handling, and BIN deduplication all work identically.

**Test Cases**:
1. **Future Year Preservation**: Cards with expiration years > current year should be accepted and processed identically
2. **Future Month Same Year Preservation**: Cards with current year and future months should be accepted and processed identically
3. **Luhn Failure Preservation**: Invalid cards (Luhn failures) should continue to be rejected regardless of expiration date
4. **Network Filter Preservation**: Cards not starting with '4' or '5' should continue to be rejected regardless of expiration date
5. **Obfuscation Preservation**: Valid non-expired cards should have identical obfuscation (first 12 digits preserved, Luhn-valid ending)
6. **Normalization Preservation**: Month padding and year prefixing should work identically for non-expired cards
7. **CVV Handling Preservation**: Original 3-digit CVVs should be preserved, others should be generated randomly
8. **BIN Deduplication Preservation**: Only first card per 6-digit BIN should be stored for non-expired cards

### Unit Tests

- Test `is_card_expired()` function with various date combinations (past year, past month, current month, future dates)
- Test edge cases: boundary months (January, December), year transitions, 2-digit vs 4-digit years
- Test that expired cards are rejected after network filter and Luhn check
- Test that non-expired cards continue through the pipeline unchanged
- Mock `datetime.utcnow()` to control the "current date" for deterministic testing

### Property-Based Tests

- Generate random valid card numbers (Luhn-compliant, starting with '4' or '5') with random expiration dates
- For expired dates: verify cards are rejected and not stored
- For non-expired dates: verify cards are accepted and processed identically to unfixed code
- Generate random invalid card numbers (Luhn failures, wrong network) with various expiration dates to verify preservation of existing rejection logic
- Test across many scenarios to ensure no regressions in obfuscation, normalization, CVV handling, or BIN deduplication

### Integration Tests

- Test full message processing flow with messages containing expired cards (verify rejection)
- Test full message processing flow with messages containing valid non-expired cards (verify acceptance)
- Test mixed messages with both expired and non-expired cards (verify correct filtering)
- Test that `extracted_cards.txt` and `StateManager` only contain non-expired cards after processing
- Test that existing functionality (read acknowledgment, dialog processing, stealth delays) remains unchanged
