# Bugfix Requirements Document

## Introduction

The card collector tool currently accepts and stores expired credit cards without validating their expiration dates against the current date. This bug allows invalid (expired) cards to be collected and stored, reducing the quality and usefulness of the collected data. The fix will add expiration date validation to reject cards that have already expired while preserving the existing behavior for valid (non-expired) cards.

## Bug Analysis

### Current Behavior (Defect)

#### Requirement 1: Card Expiration Date Validation

**User Story:** As a card collector system, I want to validate card expiration dates against the current date, so that only non-expired cards are accepted and stored.

**Acceptance Criteria:**

1. IF a card's expiration year is less than the current year (UTC), THEN THE system accepts and stores the expired card without validation

2. IF a card's expiration year equals the current year (UTC) AND the expiration month is less than the current month (UTC), THEN THE system accepts and stores the expired card without validation

3. IF a card's expiration year equals the current year (UTC) AND the expiration month equals the current month (UTC), THEN THE system accepts and stores the card (no distinction from future-dated cards)

### Expected Behavior (Correct)

#### Requirement 2: Card Expiration Date Validation

**User Story:** As a user, I want the system to validate card expiration dates, so that expired cards are rejected and only valid cards are collected.

**Acceptance Criteria:**

1. WHEN the system receives a card with expiration data, THE system SHALL extract the expiration month (1-12) and year (4-digit format) from the input

2. IF a card's expiration year is less than the current year (UTC), THEN THE system SHALL reject the card and SHALL NOT store it in extracted_cards.txt or StateManager

3. IF a card's expiration year equals the current year (UTC) AND the expiration month is less than the current month (UTC), THEN THE system SHALL reject the card and SHALL NOT store it in extracted_cards.txt or StateManager

4. IF a card's expiration year equals the current year (UTC) AND the expiration month equals the current month (UTC), THEN THE system SHALL accept the card as valid (cards are valid through the last day of their expiration month)

5. IF a card's expiration year is greater than the current year (UTC), THEN THE system SHALL accept the card as valid

6. IF a card's expiration year equals the current year (UTC) AND the expiration month is greater than the current month (UTC), THEN THE system SHALL accept the card as valid

### Unchanged Behavior (Regression Prevention)

#### Requirement 3: Preserve Existing Validation and Processing Logic

**User Story:** As a system maintainer, I want the expiration date fix to preserve all existing card validation and processing behavior, so that no regressions are introduced.

**Acceptance Criteria:**

1. IF a card has a valid expiration date (year > current year OR (year == current year AND month >= current month)) in UTC timezone AND passes Luhn validation, THEN THE system SHALL accept and store the card in extracted_cards.txt and StateManager

2. IF a card has a valid expiration date in UTC timezone BUT fails Luhn validation, THEN THE system SHALL reject the card and SHALL NOT store it

3. IF a card has a valid expiration date in UTC timezone BUT the card number does not start with '4' (Visa) or '5' (Mastercard), THEN THE system SHALL reject the card and SHALL NOT store it

4. IF a card has a valid expiration date in UTC timezone, THEN THE system SHALL obfuscate the card number by preserving the first 12 digits, generating 3 random digits for positions 13-15, and calculating digit 16 using the Luhn algorithm

5. IF a card has a valid expiration date in UTC timezone, THEN THE system SHALL normalize the expiration month to 2 digits (padding with leading zero if the input is 1 digit) and normalize the year to 4 digits (prefixing "20" if the input is 2 digits)

6. IF a card has a valid expiration date in UTC timezone AND the original CVV is exactly 3 digits, THEN THE system SHALL preserve the original CVV; OTHERWISE THE system SHALL generate a random 3-digit CVV

7. IF multiple valid cards are collected with the same 6-digit BIN prefix (first 6 digits of card number), THEN THE system SHALL store only the first card encountered for that BIN prefix (BIN-based deduplication)

8. IF valid cards are collected, THEN THE system SHALL write them to extracted_cards.txt (append mode) AND stage them via StateManager.stage_cards()
