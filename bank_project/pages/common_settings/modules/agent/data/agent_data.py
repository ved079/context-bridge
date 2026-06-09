"""
agent_data.py
-------------
Test data generators for RhythmERP Agent screen.

Location: Common Settings > Agent
URL:      /#/dynamic-screens/Agent

FORM LAYOUT (3-step stepper form — verified from live app):

  STEP 1 — Universal Fields + Address Details:
    - Party Reference         (mat-select,   optional, 503+ options)
    - Agent Name              (text input,   required, maxlength=255)
    - Phone Number            (number input, required)
    - Email                   (text input,   optional, maxlength=255)
    - Status                  (toggle switch, default Active)
    --- scroll down ---
    [Action button to add address row]
    --- Address Details Table Row ---
    - Country                 (mat-select,   required, cascading → State)
    - State                   (mat-select,   required, cascading → District)
    - District                (mat-select,   required, cascading → Taluka)
    - Taluka                  (mat-select,   required, cascading → Village)
    - Village                 (mat-select,   optional, cascading from Taluka)
    - Address                 (text input,   required, maxlength=255)
    - Pin Code                (text input,   optional, maxlength=255)

  STEP 2 — Payment Details:
    - Payment Terms           (mat-select,   optional, 9 options)
    - Preferred Payment Method(mat-select,   optional, 5 options)
    - Is GST Set Off          (toggle switch, default OFF)

  STEP 3 — Bank Details:
    [Action button to add bank row]
    --- Bank Details Table Row ---
    - Bank Name               (text input,   required, maxlength=255)
    - Branch                  (text input,   optional, maxlength=255)
    - IFSC Code               (text input,   optional, maxlength=255)
    - Account Type            (mat-select,   required, Current/Saving)
    - Account Holder Name     (text input,   required, maxlength=255)
    - Account Number          (text input,   required, maxlength=255)
    - Bank Proof              (mat-select,   required, Cancelled Cheque/Passbook)
    - Attachment              (file input,   optional, .png/.jpg/.pdf)

TABLE COLUMNS (main listing):
  - View / Edit / History   (action buttons per row)
  - Agent Name
  - Phone Number
  - Status

KNOWN BUGS (from ERP exploration):
  AGT-BUG-001 (CRITICAL): mat-select options clicked by browser do NOT reliably
             update Angular reactive form model. Must use JS workaround.
  AGT-BUG-002 (MEDIUM): Party Reference dropdown has duplicate entries.
  AGT-BUG-003 (LOW): Stepper tabs 2 & 3 locked until previous step completes.
  AGT-BUG-004 (CRITICAL): Angular inputs require get_property('value') or
             execute_script to read values. get_attribute('value') returns null.
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


def _rand_alpha(n):
    """Generate n random alphabetic characters (upper + lower)."""
    return "".join(random.choices(string.ascii_letters, k=n))


# ──────────────────────────────────────────────
# Universal Fields
# ──────────────────────────────────────────────

def generate_agent_name(prefix="AGT"):
    """Generate a valid Agent Name.

    Agent Name is required, maxlength=255. Accepts alphanumeric with spaces.
    Pattern: prefix + random alpha (e.g., 'AGT John Smith').
    """
    first = _rand_alpha(random.randint(4, 8)).capitalize()
    last = _rand_alpha(random.randint(4, 8)).capitalize()
    return f"{prefix} {first} {last}"


def generate_phone_number():
    """Generate a valid Phone Number (10-digit numeric string).

    Phone Number is required, type=number (spinbutton).
    """
    return _rand_digits(10)


def generate_email(prefix="agt"):
    """Generate a valid Email address.

    Email is optional. Format: prefix + random + @testmail.com
    """
    return f"{prefix}{_rand_digits(6)}@testmail.com"


def generate_invalid_email():
    """Generate an invalid Email (no @ symbol)."""
    return f"invalidemail{_rand_digits(4)}"


# ──────────────────────────────────────────────
# Address Fields
# ──────────────────────────────────────────────

def generate_address():
    """Generate a valid Address string (alphanumeric with spaces)."""
    streets = [
        "MG Road", "FC Road", "Station Road", "Main Street",
        "Lake Road", "Hill View", "Temple Lane", "Market Square",
    ]
    city = random.choice(["Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Solapur"])
    num = random.randint(1, 999)
    return f"{num} {random.choice(streets)} {city}"


def generate_pin_code():
    """Generate a valid Pin Code (6-digit numeric string)."""
    return _rand_digits(6)


def generate_invalid_pin_code():
    """Generate an invalid Pin Code (contains non-digits)."""
    return f"{_rand_digits(3)}ABC"


# ──────────────────────────────────────────────
# Bank Fields (within Agent form)
# ──────────────────────────────────────────────

def generate_bank_name():
    """Generate a valid Bank Name for the Agent bank details section."""
    return f"{_rand_upper(3)} {_rand_upper(8)}"


def generate_branch_name():
    """Generate a valid Branch name."""
    streets = ["Andheri", "Bandra", "Dadar", "Thane", "Vashi", "Borivali"]
    return f"{random.choice(streets)} Branch"


def generate_ifsc_code():
    """Generate a valid IFSC Code (11 chars)."""
    return f"{_rand_upper(4)}{_rand_digits(7)}"


def generate_account_holder_name():
    """Generate a valid Account Holder Name."""
    first = _rand_alpha(random.randint(4, 8)).capitalize()
    last = _rand_alpha(random.randint(4, 8)).capitalize()
    return f"{first} {last}"


def generate_account_number():
    """Generate a valid Account Number (10-16 digits)."""
    return _rand_digits(random.randint(10, 16))


# ──────────────────────────────────────────────
# Complete Valid Data for Create
# ──────────────────────────────────────────────

def generate_valid_agent_data(prefix="AGT"):
    """Generate a complete dict of valid Agent data for the Create form.

    Dropdown values set to None — must be selected from live UI at runtime.
    The page object will select specific or random valid options.
    """
    return {
        # Universal fields
        "agent_name": generate_agent_name(prefix),
        "phone_number": generate_phone_number(),
        "email": generate_email(prefix.lower()),
        "status": True,

        # Address Details
        "country": "India",
        "state": "Maharashtra",
        "district": None,  # Must select from cascaded live options
        "taluka": None,    # Must select from cascaded live options
        "village": None,   # Optional
        "address": generate_address(),
        "pin_code": generate_pin_code(),

        # Payment Details
        "payment_terms": None,             # Select from live UI
        "preferred_payment_method": None,  # Select from live UI
        "is_gst_set_off": False,

        # Bank Details
        "bank_name": generate_bank_name(),
        "branch": generate_branch_name(),
        "ifsc_code": generate_ifsc_code(),
        "account_type": None,              # "Current" or "Saving"
        "account_holder_name": generate_account_holder_name(),
        "account_number": generate_account_number(),
        "bank_proof": None,                # "Cancelled Cheque" or "Passbook"
    }


def generate_valid_edit_data():
    """Generate valid data for Edit form modifications."""
    return {
        "agent_name": generate_agent_name("EDT"),
        "phone_number": generate_phone_number(),
        "email": generate_email("edt"),
        "status": True,
        "address": generate_address(),
        "pin_code": generate_pin_code(),
        "bank_name": generate_bank_name(),
        "branch": generate_branch_name(),
        "ifsc_code": generate_ifsc_code(),
        "account_holder_name": generate_account_holder_name(),
        "account_number": generate_account_number(),
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
    return f"Agent{special}"


def generate_special_char_value():
    """Generate a value with common special characters."""
    return "!@#$%^&*()"


def generate_sql_injection():
    """SQL injection payload string."""
    return "'; DROP TABLE Agent; --"


def generate_xss_payload():
    """XSS payload string."""
    return "<script>alert('xss')</script>"


def generate_phone_with_letters():
    """Generate Phone Number with letters (invalid)."""
    return f"{_rand_digits(5)}ABC"


def generate_phone_with_special_chars():
    """Generate Phone Number with special characters (invalid)."""
    return f"{_rand_digits(5)}!@#$"


def generate_leading_trailing_spaces():
    """Agent Name with leading and trailing spaces."""
    return f"  {generate_agent_name()}  "


def generate_empty_data():
    """Return dict with all empty/None values — for mandatory field validation."""
    return {
        "agent_name": "",
        "phone_number": "",
        "email": "",
        "status": True,
        "country": "",
        "state": "",
        "district": "",
        "taluka": "",
        "village": "",
        "address": "",
        "pin_code": "",
        "payment_terms": None,
        "preferred_payment_method": None,
        "is_gst_set_off": False,
        "bank_name": "",
        "branch": "",
        "ifsc_code": "",
        "account_type": None,
        "account_holder_name": "",
        "account_number": "",
        "bank_proof": None,
    }


# ──────────────────────────────────────────────
# Expected Validation Messages
# ──────────────────────────────────────────────

VALIDATION_MSG_REQUIRED = "This field is required"

SWAL_TITLE_VALIDATION_FAILED = "Validation Failed"
SWAL_CONTENT_VALIDATION_FAILED = "Please correct the highlighted fields"
SWAL_TITLE_SUCCESS = "Your record has been added successfully!"
SWAL_TITLE_UPDATED = "Your record has been updated successfully!"
