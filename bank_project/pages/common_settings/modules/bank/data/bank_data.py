"""
bank_data.py
--------------
Test data generators for RhythmERP Bank screen.

Location: Common Settings > Bank
URL:      /#/dynamic-screens/Bank

FORM LAYOUT (simple popup — verified 2026-05-19 on live app):
  Single-page popup (NO stepper):
    - Bank Name              (text input,   required, maxlength=255, alpha-only uppercase)
    - Bank Code              (text input,   required, maxlength=255, alphanumeric)
    - Branch Name            (text input,   required, maxlength=255, alphanumeric)
    - Branch Code            (text input,   required, maxlength=255, alphanumeric)
    - Account Number         (text input,   required, maxlength=255, numeric)
    - Account Type           (mat-select,   required, searchable)
                              Options: Current, Saving
    - Swift Number           (text input,   optional, maxlength=255, SWIFT/BIC format)
    - IBAN Number            (text input,   optional, maxlength=255, IBAN format)
    - IFSC Code              (text input,   required, maxlength=255, 11 chars)
    - Cash Credit Limit      (text input,   required, maxlength=255, numeric)
    - Bank Address           (text input,   required, maxlength=255, alphanumeric+spaces)
    - GL Account             (mat-select,   required, searchable, 116+ options)
    - Is Default Bank?       (toggle switch, default No)
    - Status                 (toggle switch, default Active)

TABLE COLUMNS (main listing):
  - View / Edit / History   (action buttons per row)
  - Bank Name
  - Account Number
  - IFSC Code
  - Status

KEY RULES (verified from live application 2026-05-19):
  - Bank Name: All UPPERCASE letters only, appears to require >= 10 chars
    Existing records all follow pattern: "BankXXXXXX" (10 chars, uppercase)
    Lowercase, digits, spaces, and special characters are rejected.
  - Bank Code: Alphanumeric accepted. Numeric-only works (e.g., "5448", "C688").
    All-alpha codes may be rejected (needs further verification).
  - Branch Name: Numeric works (e.g., "5729175282"). All-alpha rejected.
  - Branch Code: Alphanumeric accepted. Both numeric and mixed work.
  - Account Number: Numeric only.
  - IFSC Code: Exactly 11 characters. "SBIN0001234" valid, "SBIN95BKGJDM" (12) invalid.
  - Swift Number: Optional. Valid SWIFT/BIC format accepted.
  - IBAN Number: Optional. Valid IBAN format accepted.
  - Cash Credit Limit: Numeric. Positive integers work.
  - Bank Address: Alphanumeric with spaces works.
  - NO formcontrolname attributes — only name attributes used.
  - Simple popup (not stepper). Submit button on create, Update on edit.
  - View popup: All fields DISABLED with character counters visible.
  - SweetAlert2: "Validation Failed" / "Your record has been added successfully!"

KNOWN BUGS:
  BUG-001 (MEDIUM): Account Type & GL Account dropdowns show NO mat-error
           text when required but empty. Only red highlight.
  BUG-002 (MEDIUM): Bank Address shows NO mat-error text when required but empty.
  BUG-003 (MEDIUM): Global search does not filter the Bank table at all.
  BUG-004 (CRITICAL): Browser-clicked mat-select options do NOT reliably update
           Angular reactive form model. Must use JS value-setter + dispatchEvent.
  BUG-005 (LOW): No Delete functionality anywhere on the Bank screen.
  BUG-006 (LOW): History button opens View popup instead of audit trail.
"""

import random
import string
from datetime import datetime


# ──────────────────────────────────────────────
# Core Data Generators
# ──────────────────────────────────────────────

def _rand_upper(n):
    """Generate n random uppercase ASCII letters."""
    return "".join(random.choices(string.ascii_uppercase, k=n))


def _rand_digits(n):
    """Generate n random digits as a string."""
    return "".join(random.choices(string.digits, k=n))


def _rand_alnum(n):
    """Generate n random alphanumeric characters."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def generate_bank_name(prefix="BNK"):
    """Generate a valid Bank Name (10 chars, all uppercase letters).

    Existing records follow pattern 'BankXXXXXX' (10 uppercase chars).
    Lowercase, digits, spaces, special chars are rejected.
    """
    return f"{prefix}{_rand_upper(7)}"  # prefix(3) + random(7) = 10


def generate_bank_code():
    """Generate a valid Bank Code (4-digit numeric string).

    Both numeric-only and alphanumeric values accepted by the ERP.
    Existing records use 4-digit numeric codes (e.g., '5448', 'C688').
    """
    return _rand_digits(4)


def generate_branch_name():
    """Generate a valid Branch Name (10-digit numeric string).

    Existing records use 10-digit numbers (e.g., '5729175282', '7769437757').
    All-alpha branch names appear to be rejected.
    """
    return _rand_digits(10)


def generate_branch_code():
    """Generate a valid Branch Code (6-digit numeric string).

    Both numeric and alphanumeric accepted (e.g., '528215', 'MBC001').
    """
    return _rand_digits(6)


def generate_account_number():
    """Generate a valid Account Number (10-digit numeric string).

    Numeric-only field. Existing records: '692215021', '2235164425'.
    """
    return _rand_digits(10)


def generate_ifsc_code():
    """Generate a valid IFSC Code (11 characters: 4 letters + 7 alphanumeric).

    Must be exactly 11 characters. 'SBIN0001234' is valid.
    12-char codes are rejected with 'Invalid IFSC'.
    """
    return f"{_rand_upper(4)}{_rand_digits(7)}"


def generate_cash_credit_limit():
    """Generate a valid Cash Credit Limit (positive integer string).

    Positive integers work. Negative / alpha values need verification.
    """
    return str(random.randint(100000, 9999999))


def generate_bank_address():
    """Generate a valid Bank Address (alphanumeric with spaces).

    'Test Address Mumbai', '456 Andheri West Mumbai' both accepted.
    """
    streets = [
        "MG Road", "FC Road", "Andheri West", "Bandra East",
        "Pune", "Mumbai Central", "Thane West", "Navi Mumbai",
    ]
    city = random.choice(["Mumbai", "Pune", "Nagpur", "Nashik", "Thane"])
    return f"{random.randint(1, 999)} {random.choice(streets)} {city}"


def generate_swift_number():
    """Generate a valid SWIFT/BIC Number (8 or 11 uppercase alphanumeric chars).

    Standard SWIFT/BIC format: 8-char bank code or 11-char with branch.
    'SBIINBB123', 'SBIINBBXXX' both accepted.
    Empty value also accepted (optional field).
    """
    return f"{_rand_upper(8)}{_rand_upper(3)}"  # 11-char BIC with branch


def generate_iban_number():
    """Generate a valid IBAN Number.

    'IN1234567890' and 'GB29NWBK60161331926819' both accepted.
    Empty value also accepted (optional field).
    """
    return f"IN{_rand_digits(2)}{_rand_upper(4)}{_rand_digits(7)}"


# ──────────────────────────────────────────────
# Complete Valid Data for Create
# ──────────────────────────────────────────────

def generate_valid_bank_data(prefix="BNK"):
    """Generate a complete dict of valid bank data for the Create form.

    Dropdown values set to None — must be populated from live UI at runtime.
    The calling code or page object will select random valid options.
    """
    return {
        "bank_name": generate_bank_name(prefix),
        "bank_code": generate_bank_code(),
        "branch_name": generate_branch_name(),
        "branch_code": generate_branch_code(),
        "account_number": generate_account_number(),
        "account_type": None,       # Pick from live UI (REQUIRED) — "Current" or "Saving"
        "swift_number": generate_swift_number(),
        "iban_number": generate_iban_number(),
        "ifsc_code": generate_ifsc_code(),
        "cash_credit_limit": generate_cash_credit_limit(),
        "bank_address": generate_bank_address(),
        "gl_account": None,         # Pick from live UI (REQUIRED) — 116+ options
        "is_default_bank": False,   # Toggle: No (default)
        "status": True,             # Toggle: Active (default)
    }


def generate_valid_edit_data():
    """Generate valid data for Edit form modifications.

    Bank Name is editable in Edit mode (unlike Item Master).
    Dropdown values set to None — caller should specify or let
    page object preserve existing selections.
    """
    return {
        "bank_name": generate_bank_name("EDT"),
        "bank_code": generate_bank_code(),
        "branch_name": generate_branch_name(),
        "branch_code": generate_branch_code(),
        "account_number": generate_account_number(),
        "swift_number": generate_swift_number(),
        "iban_number": generate_iban_number(),
        "ifsc_code": generate_ifsc_code(),
        "cash_credit_limit": generate_cash_credit_limit(),
        "bank_address": generate_bank_address(),
        "is_default_bank": False,
        "status": True,
    }


# ──────────────────────────────────────────────
# Validation Test Data Helpers
# ──────────────────────────────────────────────

def generate_spaces_only(length=10):
    """Generate a string of only spaces."""
    return " " * length


def generate_string_255():
    """Generate a string of exactly 255 characters (max boundary)."""
    return "A" * 255


def generate_string_256():
    """Generate a string of exactly 256 characters (exceeds max)."""
    return "A" * 256


def generate_special_char_name():
    """Generate a name with special characters."""
    special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
    return f"Bank{special}"


def generate_special_char_value():
    """Generate a value with common special characters."""
    return "!@#$%^&*()"


def generate_sql_injection():
    """SQL injection payload string."""
    return "'; DROP TABLE Bank; --"


def generate_xss_payload():
    """XSS payload string."""
    return "<script>alert('xss')</script>"


def generate_negative_limit():
    """Negative Cash Credit Limit value."""
    return f"-{random.randint(1, 999)}"


def generate_zero_limit():
    """Zero Cash Credit Limit value."""
    return "0"


def generate_alpha_limit():
    """Alphabetic Cash Credit Limit value."""
    return "abcDEF"


def generate_special_char_limit():
    """Special character Cash Credit Limit value."""
    return "!@#$"


def generate_limit_with_spaces():
    """Spaces-only Cash Credit Limit value."""
    return "   "


def generate_leading_trailing_spaces():
    """Bank Name with leading and trailing spaces."""
    return f"  {generate_bank_name()}  "


def generate_lowercase_bank_name():
    """Generate Bank Name with lowercase letters (should be invalid)."""
    return f"bank{_rand_upper(7)}".lower()


def generate_bank_name_with_digits():
    """Generate Bank Name with digits (should be invalid)."""
    return f"BNK{_rand_digits(7)}"


def generate_bank_name_too_short():
    """Generate Bank Name with < 10 chars (should be invalid)."""
    return f"BNK{_rand_upper(2)}"  # 5 chars


def generate_ifsc_too_short():
    """Generate IFSC Code with < 11 chars (should be invalid)."""
    return f"{_rand_upper(4)}{_rand_digits(5)}"  # 9 chars


def generate_ifsc_too_long():
    """Generate IFSC Code with > 11 chars (should be invalid)."""
    return f"{_rand_upper(4)}{_rand_digits(8)}"  # 12 chars


def generate_alpha_branch_name():
    """Generate Branch Name with letters only (may be invalid)."""
    return "MumbaiBranch"


def generate_alpha_account_number():
    """Generate Account Number with letters (should be invalid)."""
    return "ABCDEFGHIJ"


def generate_empty_data():
    """Return dict with all empty strings — for mandatory field validation."""
    return {
        "bank_name": "",
        "bank_code": "",
        "branch_name": "",
        "branch_code": "",
        "account_number": "",
        "account_type": "",
        "swift_number": "",
        "iban_number": "",
        "ifsc_code": "",
        "cash_credit_limit": "",
        "bank_address": "",
        "gl_account": "",
        "is_default_bank": False,
        "status": True,
    }


def generate_partial_required_data():
    """Return dict with only some required fields filled — for partial validation test."""
    return {
        "bank_name": generate_bank_name("Partial"),
        "bank_code": "",
        "branch_name": "",
        "branch_code": "",
        "account_number": "",
        "account_type": "",
        "swift_number": "",
        "iban_number": "",
        "ifsc_code": "",
        "cash_credit_limit": "",
        "bank_address": "",
        "gl_account": "",
        "is_default_bank": False,
        "status": True,
    }


# ──────────────────────────────────────────────
# Expected Validation Messages
# ──────────────────────────────────────────────

VALIDATION_MSG_REQUIRED = "This field is required"
VALIDATION_MSG_INVALID_BANK_NAME = "Invalid Bank Name"
VALIDATION_MSG_INVALID_BANK_CODE = "Invalid Bank Code"
VALIDATION_MSG_INVALID_BRANCH_NAME = "Invalid Name"
VALIDATION_MSG_INVALID_IFSC = "Invalid IFSC"
VALIDATION_MSG_INVALID_SWIFT = "Invalid Swift Number"
VALIDATION_MSG_INVALID_IBAN = "Invalid IBAN Number"

SWAL_TITLE_VALIDATION_FAILED = "Validation Failed"
SWAL_CONTENT_VALIDATION_FAILED = "Please correct the highlighted fields"
SWAL_TITLE_SUCCESS = "Your record has been added successfully!"
SWAL_TITLE_UPDATED = "Your record has been updated successfully!"
