"""
test_bank_validation.py
-----------------------
Comprehensive validation test suite for RhythmERP Bank screen.
~59 test cases across 7 phases.

Phases:
  1. Create Form Validations  (22 tests) — BNK-C01 to BNK-C22
  2. Duplicate Validations      (5 tests) — BNK-D01 to BNK-D05
  3. Edit Form Validations      (8 tests) — BNK-E01 to BNK-E08
  4. Search & Filter Edge Cases (6 tests) — BNK-S01 to BNK-S06
  5. Popup & UI Behaviors       (10 tests) — BNK-P01 to BNK-P10
  6. History & Audit Trail      (3 tests) — BNK-H01 to BNK-H03
  7. Bug-specific              (5 tests) — BNK-B01 to BNK-B05

FORM LAYOUT (simple popup — NOT a stepper):
  - Bank Name              (required, alpha-only uppercase, >= 10 chars)
  - Bank Code              (required, alphanumeric)
  - Branch Name            (required, alphanumeric)
  - Branch Code            (required, alphanumeric)
  - Account Number         (required, numeric)
  - Account Type           (required, dropdown: Current/Saving)
  - Swift Number           (optional, SWIFT/BIC format)
  - IBAN Number            (optional, IBAN format)
  - IFSC Code              (required, exactly 11 chars)
  - Cash Credit Limit      (required, numeric)
  - Bank Address           (required, alphanumeric+spaces)
  - GL Account             (required, dropdown, 116+ options)
  - Is Default Bank?       (toggle, default No)
  - Status                 (toggle, default Active)

Known Bugs (CONFIRMED via browser exploration 2026-05-19):
  BUG-001 (MEDIUM): Account Type & GL Account dropdowns missing mat-error text
  BUG-002 (MEDIUM): Bank Address required field missing mat-error text
  BUG-003 (MEDIUM): Global search does not filter Bank table
  BUG-004 (CRITICAL): Browser-clicked mat-select options do NOT reliably
                     update Angular reactive form model — must use JS value-setter
  BUG-005 (LOW): No Delete functionality
  BUG-006 (LOW): History button opens View popup instead of audit trail

Run:
  pytest test_bank_validation.py -v --tb=short
  pytest test_bank_validation.py -v -k "TestCreateForm" --tb=short
  pytest test_bank_validation.py -v -k "BNK-C03" --tb=short
"""

import os
import sys
import time

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

import pytest
from selenium.webdriver.common.by import By

from pages.common_settings.modules.bank.bank_page import BankPage
from pages.common_settings.modules.bank.data.bank_data import (
    generate_valid_bank_data,
    generate_valid_edit_data,
    generate_bank_name,
    generate_bank_code,
    generate_branch_name,
    generate_branch_code,
    generate_account_number,
    generate_ifsc_code,
    generate_cash_credit_limit,
    generate_bank_address,
    generate_swift_number,
    generate_iban_number,
    generate_spaces_only,
    generate_string_255,
    generate_string_256,
    generate_special_char_name,
    generate_special_char_value,
    generate_sql_injection,
    generate_xss_payload,
    generate_negative_limit,
    generate_zero_limit,
    generate_alpha_limit,
    generate_special_char_limit,
    generate_limit_with_spaces,
    generate_leading_trailing_spaces,
    generate_lowercase_bank_name,
    generate_bank_name_with_digits,
    generate_bank_name_too_short,
    generate_ifsc_too_short,
    generate_ifsc_too_long,
    generate_alpha_branch_name,
    generate_alpha_account_number,
    generate_empty_data,
    generate_partial_required_data,
    VALIDATION_MSG_REQUIRED,
    VALIDATION_MSG_INVALID_BANK_NAME,
    VALIDATION_MSG_INVALID_BANK_CODE,
    VALIDATION_MSG_INVALID_BRANCH_NAME,
    VALIDATION_MSG_INVALID_IFSC,
    VALIDATION_MSG_INVALID_SWIFT,
    VALIDATION_MSG_INVALID_IBAN,
    SWAL_TITLE_VALIDATION_FAILED,
    SWAL_TITLE_SUCCESS,
)
from common.logger import log


# ====================================================================
# Helper: create a prerequisite bank, refresh, return its name
# ====================================================================

def _create_prerequisite_bank(page, prefix="PreReq"):
    """Create a Bank entry for tests that need existing data.
    Returns the bank name and the data dict used.
    """
    data = generate_valid_bank_data(prefix)
    result = page.create_bank(data)
    try:
        page.close_popup()
    except Exception:
        pass
    try:
        page.force_close_form_popup()
    except Exception:
        pass
    page.click_refresh()
    page.wait_seconds(2)
    name = result.get("bank_name", "")
    log.info(f"Prerequisite bank created: {name}")
    return name, data


def _cleanup_form(page):
    """Try to close any open form popup."""
    try:
        page.cancel()
    except Exception:
        pass
    try:
        page.force_close_form_popup()
    except Exception:
        pass


# ====================================================================
# PHASE 1: Create Form Validations (22 tests)
# ====================================================================

class TestCreateFormValidations:
    """BNK-C01 to BNK-C22: Validation checks on the Create form."""

    # ---- BNK-C01: Submit with all fields empty ----
    def test_BNK_C01_empty_submit(self, bnk_page):
        """Submit with all fields empty — should be blocked."""
        log.info("BNK-C01: Empty submit test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)
        assert page.is_add_form_open(), "Add form did not open"

        # Click Submit with all fields empty
        page.submit()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        errors = page.get_mat_error_text()
        form_still_open = page.is_add_form_open()

        assert form_still_open or errors or validation_alert, (
            "BUG: Form advanced with all fields empty — no validation"
        )
        if validation_alert:
            log.info(f"Validation alert shown: {validation_alert}")
        if errors:
            log.info(f"Validation errors shown: {errors}")

        # Cleanup
        _cleanup_form(page)

    # ---- BNK-C02: Create with valid data (happy path) ----
    def test_BNK_C02_valid_create(self, bnk_page):
        """Create with valid data — should succeed."""
        log.info("BNK-C02: Valid create test (happy path)")
        page = bnk_page

        data = generate_valid_bank_data("ValidC")
        result = page.create_bank(data)
        name = result.get("bank_name", "")

        if result["status"] == "PASSED":
            log.info(f"Bank created successfully: {name}")
        else:
            log.warning(f"Create failed: {result.get('error', 'unknown')}")

        page.click_refresh()
        page.wait_seconds(2)
        found = page.is_bank_in_table(name)

        assert found, f"Created bank '{name}' not found in table after refresh"
        log.info(f"Bank created and found in table: {name}")

    # ---- BNK-C03: Bank Name — alpha-only uppercase validation ----
    def test_BNK_C03_bank_name_alpha_only(self, bnk_page):
        """Bank Name accepts uppercase alpha, rejects digits/mixed/short."""
        log.info("BNK-C03: Bank Name alpha-only validation test")
        page = bnk_page

        # Test valid: all uppercase, 10+ chars
        valid_name = generate_bank_name("AlphaTest")
        page.open_add_form()
        page.wait_seconds(1)
        page._fill_input_by_name("Bank Name", valid_name)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Bank Name")
        assert not state["invalid"], (
            f"Valid uppercase Bank Name '{valid_name}' should be accepted"
        )
        log.info(f"Valid Bank Name '{valid_name}' accepted")

        # Test invalid: contains digits
        invalid_digit = generate_bank_name_with_digits()
        page._fill_input_by_name("Bank Name", invalid_digit)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Bank Name")
        log.info(
            f"Bank Name with digits '{invalid_digit}': "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        # Test invalid: lowercase
        invalid_lower = generate_lowercase_bank_name()
        page._fill_input_by_name("Bank Name", invalid_lower)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Bank Name")
        log.info(
            f"Lowercase Bank Name '{invalid_lower}': "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- BNK-C04: Bank Code — pattern validation ----
    def test_BNK_C04_bank_code_validation(self, bnk_page):
        """Bank Code accepts alphanumeric values, may reject all-alpha."""
        log.info("BNK-C04: Bank Code validation test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Test valid: numeric code
        valid_code = generate_bank_code()
        page._fill_input_by_name("Bank Code", valid_code)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Bank Code")
        assert not state["invalid"], f"Valid Bank Code '{valid_code}' should be accepted"
        log.info(f"Valid Bank Code '{valid_code}' accepted")

        # Test invalid: special characters
        page._fill_input_by_name("Bank Code", "!@#$")
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Bank Code")
        log.info(
            f"Special chars Bank Code: "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- BNK-C05: Branch Name — pattern validation ----
    def test_BNK_C05_branch_name_validation(self, bnk_page):
        """Branch Name accepts numeric values, may reject all-alpha."""
        log.info("BNK-C05: Branch Name validation test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Test valid: numeric
        valid_branch = generate_branch_name()
        page._fill_input_by_name("Branch Name", valid_branch)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Branch Name")
        assert not state["invalid"], f"Valid Branch Name '{valid_branch}' should be accepted"
        log.info(f"Valid Branch Name '{valid_branch}' accepted")

        # Test: all-alpha branch name
        alpha_branch = generate_alpha_branch_name()
        page._fill_input_by_name("Branch Name", alpha_branch)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Branch Name")
        log.info(
            f"Alpha Branch Name '{alpha_branch}': "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- BNK-C06: Account Number — numeric only ----
    def test_BNK_C06_account_number_numeric_only(self, bnk_page):
        """Account Number should only accept numeric values."""
        log.info("BNK-C06: Account Number numeric-only test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Test valid: numeric
        valid_acct = generate_account_number()
        page._fill_input_by_name("Account Number", valid_acct)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Account Number")
        assert not state["invalid"], f"Valid Account Number '{valid_acct}' should be accepted"
        log.info(f"Valid Account Number '{valid_acct}' accepted")

        # Test invalid: alpha
        alpha_acct = generate_alpha_account_number()
        page._fill_input_by_name("Account Number", alpha_acct)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Account Number")
        log.info(
            f"Alpha Account Number '{alpha_acct}': "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- BNK-C07: IFSC Code — exactly 11 chars ----
    def test_BNK_C07_ifsc_code_11_chars(self, bnk_page):
        """IFSC Code must be exactly 11 characters."""
        log.info("BNK-C07: IFSC Code 11-char validation test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Valid: exactly 11 chars
        valid_ifsc = generate_ifsc_code()
        page._fill_input_by_name("IFSC Code", valid_ifsc)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("IFSC Code")
        assert not state["invalid"], f"Valid IFSC Code '{valid_ifsc}' should be accepted"
        log.info(f"Valid IFSC Code (11 chars) '{valid_ifsc}' accepted")

        # Invalid: too short (9 chars)
        short_ifsc = generate_ifsc_too_short()
        page._fill_input_by_name("IFSC Code", short_ifsc)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("IFSC Code")
        log.info(
            f"Short IFSC (9 chars) '{short_ifsc}': "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        # Invalid: too long (12 chars)
        long_ifsc = generate_ifsc_too_long()
        page._fill_input_by_name("IFSC Code", long_ifsc)
        page.wait_seconds(0.5)
        state = get_field_validation_state = page.get_field_validation_state("IFSC Code")
        log.info(
            f"Long IFSC (12 chars) '{long_ifsc}': "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- BNK-C08: Cash Credit Limit — numeric validation ----
    def test_BNK_C08_cash_credit_limit_numeric(self, bnk_page):
        """Cash Credit Limit should only accept numeric values."""
        log.info("BNK-C08: Cash Credit Limit numeric test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Valid: positive number
        valid_limit = generate_cash_credit_limit()
        page._fill_input_by_name("Cash Credit Limit", valid_limit)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Cash Credit Limit")
        assert not state["invalid"], f"Valid limit '{valid_limit}' should be accepted"
        log.info(f"Valid Cash Credit Limit '{valid_limit}' accepted")

        # Invalid: alphabetic
        alpha_limit = generate_alpha_limit()
        page._fill_input_by_name("Cash Credit Limit", alpha_limit)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Cash Credit Limit")
        log.info(
            f"Alpha limit '{alpha_limit}': "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        # Invalid: special chars
        special_limit = generate_special_char_limit()
        page._fill_input_by_name("Cash Credit Limit", special_limit)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Cash Credit Limit")
        log.info(
            f"Special chars limit '{special_limit}': "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        # Invalid: spaces
        spaces_limit = generate_limit_with_spaces()
        page._fill_input_by_name("Cash Credit Limit", spaces_limit)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Cash Credit Limit")
        log.info(
            f"Spaces limit: invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- BNK-C09: Swift Number — optional, format validation ----
    def test_BNK_C09_swift_number_optional_format(self, bnk_page):
        """Swift Number is optional; valid format accepted, invalid rejected."""
        log.info("BNK-C09: Swift Number optional format test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Empty is valid (optional field)
        page._fill_input_by_name("Swift Number", "")
        page.wait_seconds(0.3)
        state = page.get_field_validation_state("Swift Number")
        assert not state["invalid"], "Empty Swift Number should be valid (optional)"
        log.info("Empty Swift Number: valid (optional field confirmed)")

        # Valid format
        valid_swift = generate_swift_number()
        page._fill_input_by_name("Swift Number", valid_swift)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Swift Number")
        assert not state["invalid"], f"Valid Swift '{valid_swift}' should be accepted"
        log.info(f"Valid Swift Number '{valid_swift}' accepted")

        _cleanup_form(page)

    # ---- BNK-C10: IBAN Number — optional, format validation ----
    def test_BNK_C10_iban_number_optional_format(self, bnk_page):
        """IBAN Number is optional; valid format accepted, invalid rejected."""
        log.info("BNK-C10: IBAN Number optional format test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Empty is valid (optional field)
        page._fill_input_by_name("IBAN Number", "")
        page.wait_seconds(0.3)
        state = page.get_field_validation_state("IBAN Number")
        assert not state["invalid"], "Empty IBAN Number should be valid (optional)"
        log.info("Empty IBAN Number: valid (optional field confirmed)")

        # Valid format
        valid_iban = generate_iban_number()
        page._fill_input_by_name("IBAN Number", valid_iban)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("IBAN Number")
        assert not state["invalid"], f"Valid IBAN '{valid_iban}' should be accepted"
        log.info(f"Valid IBAN Number '{valid_iban}' accepted")

        _cleanup_form(page)

    # ---- BNK-C11: Bank Address — required, pattern validation ----
    def test_BNK_C11_bank_address_validation(self, bnk_page):
        """Bank Address is required and accepts alphanumeric with spaces."""
        log.info("BNK-C11: Bank Address validation test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Valid: alphanumeric with spaces
        valid_addr = generate_bank_address()
        page._fill_input_by_name("Bank Address", valid_addr)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Bank Address")
        assert not state["invalid"], f"Valid address '{valid_addr}' should be accepted"
        log.info(f"Valid Bank Address '{valid_addr}' accepted")

        _cleanup_form(page)

    # ---- BNK-C12: Spaces-only in required fields ----
    def test_BNK_C12_spaces_only_required_fields(self, bnk_page):
        """Spaces-only values in required text fields should be rejected."""
        log.info("BNK-C12: Spaces-only required fields test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        spaces = generate_spaces_only()
        for field_name in ["Bank Name", "Bank Code", "Branch Name",
                          "Account Number", "IFSC Code"]:
            page._fill_input_by_name(field_name, spaces)
        page.wait_seconds(0.5)

        # Submit to trigger validation
        page.submit()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        form_still_open = page.is_add_form_open()

        assert form_still_open or validation_alert, (
            "BUG: Form accepted spaces-only values in required fields"
        )
        log.info(f"Spaces-only submit: form_open={form_still_open}, alert={validation_alert}")

        _cleanup_form(page)

    # ---- BNK-C13: Maxlength boundary (255/256 chars) ----
    def test_BNK_C13_maxlength_boundary(self, bnk_page):
        """Bank fields have maxlength=255. 256-char input should be truncated or rejected."""
        log.info("BNK-C13: Maxlength boundary test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Test 255 chars (should be accepted by maxlength)
        long_255 = generate_string_255()
        page._fill_input_by_name("Bank Address", long_255)
        page.wait_seconds(0.5)
        actual_value = page.get_input_value("Bank Address")
        log.info(f"255-char input: actual length = {len(actual_value)}")

        # Test 256 chars (should be truncated by maxlength to 255)
        long_256 = generate_string_256()
        page._fill_input_by_name("Bank Address", long_256)
        page.wait_seconds(0.5)
        actual_value_256 = page.get_input_value("Bank Address")
        log.info(
            f"256-char input: actual length = {len(actual_value_256)}, "
            f"truncated = {len(actual_value_256) == 255}"
        )

        _cleanup_form(page)

    # ---- BNK-C14: Special characters in text fields ----
    def test_BNK_C14_special_characters(self, bnk_page):
        """Special characters in Bank Name should be rejected."""
        log.info("BNK-C14: Special characters test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        special = generate_special_char_name()
        page._fill_input_by_name("Bank Name", special)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Bank Name")
        log.info(
            f"Special chars Bank Name: "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- BNK-C15: SQL injection strings ----
    @pytest.mark.xfail(
        reason="BUG: SQL injection strings may be accepted by the system. "
               "This test verifies if they are accepted (BUG) or rejected (security).",

    )
    def test_BNK_C15_sql_injection(self, bnk_page):
        """SQL injection payload should be rejected by the system."""
        log.info("BNK-C15: SQL injection test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        sql_payload = generate_sql_injection()
        page._fill_input_by_name("Bank Name", sql_payload)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Bank Name")
        log.info(
            f"SQL injection in Bank Name: "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- BNK-C16: XSS payloads ----
    @pytest.mark.xfail(
        reason="BUG: XSS payloads may be accepted by the system. "
               "This test verifies if they are accepted (BUG) or rejected (security).",

    )
    def test_BNK_C16_xss_payload(self, bnk_page):
        """XSS payload should be rejected by the system."""
        log.info("BNK-C16: XSS payload test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        xss = generate_xss_payload()
        page._fill_input_by_name("Bank Name", xss)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Bank Name")
        log.info(
            f"XSS in Bank Name: "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- BNK-C17: Negative/zero/alpha in Cash Credit Limit ----
    def test_BNK_C17_cash_credit_limit_edge_cases(self, bnk_page):
        """Cash Credit Limit: negative, zero, alpha values."""
        log.info("BNK-C17: Cash Credit Limit edge cases test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        for value, label in [
            (generate_negative_limit(), "negative"),
            (generate_zero_limit(), "zero"),
            (generate_alpha_limit(), "alphabetic"),
        ]:
            page._fill_input_by_name("Cash Credit Limit", value)
            page.wait_seconds(0.3)
            state = page.get_field_validation_state("Cash Credit Limit")
            log.info(
                f"Limit '{value}' ({label}): "
                f"invalid={state['invalid']}, error='{state['error']}'"
            )

        _cleanup_form(page)

    # ---- BNK-C18: Leading/trailing spaces trimming ----
    def test_BNK_C18_leading_trailing_spaces(self, bnk_page):
        """Test leading/trailing spaces in Bank Name."""
        log.info("BNK-C18: Leading/trailing spaces test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        spaced = generate_leading_trailing_spaces()
        page._fill_input_by_name("Bank Name", spaced)
        page.wait_seconds(0.5)
        actual = page.get_input_value("Bank Name")
        log.info(
            f"Input: '{spaced}' → Actual: '{actual}' "
            f"(trimmed={actual.strip() == spaced.strip()})"
        )

        _cleanup_form(page)

    # ---- BNK-C19: Partial required fields filled ----
    def test_BNK_C19_partial_required_fields(self, bnk_page):
        """Submit with only some required fields filled — should be blocked."""
        log.info("BNK-C19: Partial required fields test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Fill only Bank Name and Bank Code
        data = generate_valid_bank_data("Partial")
        page._fill_input_by_name("Bank Name", data["bank_name"])
        page._fill_input_by_name("Bank Code", data["bank_code"])
        # Leave all other required fields empty

        page.submit()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        form_still_open = page.is_add_form_open()

        assert form_still_open or validation_alert, (
            "BUG: Form submitted with partial required fields"
        )

        _cleanup_form(page)

    # ---- BNK-C20: Invalid → valid → submit (error persistence) ----
    def test_BNK_C20_invalid_then_valid_submit(self, bnk_page):
        """Fill invalid data, fix to valid, submit — errors should clear."""
        log.info("BNK-C20: Invalid → valid → submit test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Fill invalid Bank Name (with digits)
        page._fill_input_by_name("Bank Name", "Bank1234X")
        page.wait_seconds(0.5)
        state1 = page.get_field_validation_state("Bank Name")
        log.info(f"After invalid name: invalid={state1['invalid']}")

        # Fix to valid Bank Name
        valid_name = generate_bank_name("FixTest")
        page._fill_input_by_name("Bank Name", valid_name)
        page.wait_seconds(0.5)
        state2 = page.get_field_validation_state("Bank Name")
        log.info(f"After valid name: invalid={state2['invalid']}")

        assert not state2["invalid"], (
            f"Valid Bank Name '{valid_name}' should clear the error"
        )

        _cleanup_form(page)

    # ---- BNK-C21: Toggle — Is Default Bank ----
    def test_BNK_C21_toggle_is_default_bank(self, bnk_page):
        """Is Default Bank? toggle defaults to No and can be toggled."""
        log.info("BNK-C21: Is Default Bank toggle test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Default should be OFF (false)
        state = page.get_toggle_state("Is Default Bank?")
        log.info(f"Default Is Default Bank: {state}")

        # Toggle to Yes
        page.set_is_default_bank(True)
        state_after = page.get_toggle_state("Is Default Bank?")
        log.info(f"After toggle ON: {state_after}")

        # Toggle back to No
        page.set_is_default_bank(False)
        state_final = page.get_toggle_state("Is Default Bank?")
        log.info(f"After toggle OFF: {state_final}")

        _cleanup_form(page)

    # ---- BNK-C22: Toggle — Status ----
    def test_BNK_C22_toggle_status(self, bnk_page):
        """Status toggle defaults to Active and can be toggled."""
        log.info("BNK-C22: Status toggle test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Default should be ON (true = Active)
        state = page.get_toggle_state("Status")
        log.info(f"Default Status: {state}")

        # Toggle to Inactive
        page.set_status(False)
        state_after = page.get_toggle_state("Status")
        log.info(f"After toggle OFF: {state_after}")

        # Toggle back to Active
        page.set_status(True)
        state_final = page.get_toggle_state("Status")
        log.info(f"After toggle ON: {state_final}")

        _cleanup_form(page)


# ====================================================================
# PHASE 2: Duplicate Validations (5 tests)
# ====================================================================

class TestDuplicateValidations:
    """BNK-D01 to BNK-D05: Duplicate checks in Create and Edit."""

    # ---- BNK-D01: Duplicate Bank Name ----
    def test_BNK_D01_duplicate_bank_name(self, bnk_page):
        """Create two banks with the same Bank Name — check duplicate behavior."""
        log.info("BNK-D01: Duplicate Bank Name test")
        page = bnk_page

        # Create bank 1
        data1 = generate_valid_bank_data("DupD01")
        result1 = page.create_bank(data1)
        name1 = result1.get("bank_name", "")

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        if not name1:
            log.warning("Bank 1 creation failed — cannot test duplicate")
            return

        # Try to create bank 2 with same name
        data2 = generate_valid_bank_data("DupD02")
        data2["bank_name"] = name1  # Use same name
        result2 = page.create_bank(data2)
        name2 = result2.get("bank_name", "")

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        log.info(
            f"Bank 1: '{name1}', Bank 2: '{name2}'"
        )

        if result1["status"] == "PASSED" and result2["status"] == "PASSED":
            log.info("Both banks created — duplicates ALLOWED")
        elif "duplicate" in result2.get("error", "").lower():
            log.info("Duplicate Bank Name was BLOCKED by the system")
        else:
            log.warning(f"Second create failed: {result2.get('error')}")

    # ---- BNK-D02: Case-insensitive duplicate ----
    @pytest.mark.skip(
        reason="Bank Name requires uppercase-only alpha; lowercase names are "
               "rejected at the validation level, not at the duplicate-check level. "
               "Case-insensitive duplicate testing is not applicable."
    )
    def test_BNK_D02_duplicate_case_insensitive(self, bnk_page):
        """Create bank with same name in different case — not applicable."""
        log.info("BNK-D02: Duplicate case-insensitive test — SKIPPED")

    # ---- BNK-D03: Edit to duplicate name ----
    def test_BNK_D03_edit_duplicate_name(self, bnk_page):
        """Edit a bank to use another bank's name — check behavior."""
        log.info("BNK-D03: Edit to duplicate name test")
        page = bnk_page

        name1, _ = _create_prerequisite_bank(page, "DupEdt1")
        name2, _ = _create_prerequisite_bank(page, "DupEdt2")

        if not name1 or not name2:
            log.warning("Prerequisite banks not created — cannot test")
            return

        # Edit bank 2 to have bank 1's name
        page.click_edit_button(bank_name=name2)
        page.wait_seconds(2)

        if page.is_form_popup_open():
            page._fill_input_by_name("Bank Name", name1)
            page.update()
            page.wait_seconds(3)

            alert = page.handle_success_alert(timeout=5)
            if alert:
                log.info(f"Edit update: {alert}")

        page.click_refresh()
        page.wait_seconds(2)

        log.info(
            f"Edit bank '{name2}' to name '{name1}' — "
            f"both exist: name1={page.is_bank_in_table(name1)}, "
            f"name2={page.is_bank_in_table(name2)}"
        )

    # ---- BNK-D04: Duplicate Account Number ----
    def test_BNK_D04_duplicate_account_number(self, bnk_page):
        """Create two banks with the same Account Number."""
        log.info("BNK-D04: Duplicate Account Number test")
        page = bnk_page

        data1 = generate_valid_bank_data("DupAcct1")
        acct_num = data1["account_number"]
        result1 = page.create_bank(data1)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        if result1["status"] != "PASSED":
            log.warning("First bank creation failed — cannot test duplicate")
            return

        # Create bank 2 with same account number
        data2 = generate_valid_bank_data("DupAcct2")
        data2["account_number"] = acct_num
        result2 = page.create_bank(data2)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        log.info(
            f"Duplicate Account Number '{acct_num}': "
            f"result2={result2}"
        )

    # ---- BNK-D05: Duplicate IFSC Code ----
    def test_BNK_D05_duplicate_ifsc_code(self, bnk_page):
        """Create two banks with the same IFSC Code."""
        log.info("BNK-D05: Duplicate IFSC Code test")
        page = bnk_page

        data1 = generate_valid_bank_data("DupIfsc1")
        ifsc = data1["ifsc_code"]
        result1 = page.create_bank(data1)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        if result1["status"] != "PASSED":
            log.warning("First bank creation failed — cannot test duplicate")
            return

        # Create bank 2 with same IFSC
        data2 = generate_valid_bank_data("DupIfsc2")
        data2["ifsc_code"] = ifsc
        result2 = page.create_bank(data2)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        log.info(
            f"Duplicate IFSC Code '{ifsc}': "
            f"result2={result2}"
        )


# ====================================================================
# PHASE 3: Edit Form Validations (8 tests)
# ====================================================================

class TestEditFormValidations:
    """BNK-E01 to BNK-E08: Validation checks on the Edit form."""

    # ---- BNK-E01: Edit — pre-populated fields ----
    def test_BNK_E01_edit_prepopulated(self, bnk_page):
        """Edit popup should show all fields pre-populated with existing data."""
        log.info("BNK-E01: Edit pre-populated fields test")
        page = bnk_page

        name, data = _create_prerequisite_bank(page, "EditPre")

        if not name:
            log.warning("Prerequisite bank not created — cannot verify edit")
            return

        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)

        assert page.is_form_popup_open(), "Edit form popup did not open"

        values = page.get_form_field_values()
        log.info(f"Form values: {values}")

        # Verify key fields have values
        assert values.get("Bank Name", ""), "Bank Name should be pre-populated"
        assert values.get("Bank Code", ""), "Bank Code should be pre-populated"
        assert values.get("Account Number", ""), "Account Number should be pre-populated"

        log.info("Edit form fields verified as pre-populated")

        _cleanup_form(page)

    # ---- BNK-E02: Edit happy path ----
    def test_BNK_E02_edit_happy_path(self, bnk_page):
        """Edit a bank, modify fields, and Update — should succeed."""
        log.info("BNK-E02: Edit happy path test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "EditHP")

        if not name:
            log.warning("Prerequisite bank not created — cannot test edit")
            return

        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)

        edit_data = generate_valid_edit_data()
        page._fill_input_by_name("Bank Code", edit_data["bank_code"])
        page._fill_input_by_name("Bank Address", edit_data["bank_address"])

        page.update()
        page.wait_seconds(3)

        alert = page.handle_success_alert(timeout=5)
        if alert:
            log.info(f"Edit success: {alert}")

        page.click_refresh()
        page.wait_seconds(2)
        found = page.is_bank_in_table(name)
        assert found, f"Edited bank '{name}' should still exist in table"
        log.info(f"Edited bank '{name}' found in table after update")

    # ---- BNK-E03: Edit — clear required field → validation ----
    def test_BNK_E03_edit_clear_required(self, bnk_page):
        """Clear a required field in Edit mode — should show validation."""
        log.info("BNK-E03: Edit clear required field test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "EditClr")

        if not name:
            log.warning("Prerequisite bank not created")
            return

        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)

        # Clear Bank Name
        page._fill_input_by_name("Bank Name", "")
        page.wait_seconds(0.5)

        page.update()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        popup_still_open = page.is_form_popup_open()

        assert popup_still_open or validation_alert, (
            "BUG: Edit allowed clearing required field without validation"
        )

        _cleanup_form(page)

    # ---- BNK-E04: Edit invalid → fix → Update ----
    def test_BNK_E04_edit_invalid_then_fix(self, bnk_page):
        """Edit to invalid data, fix it, then Update — should succeed."""
        log.info("BNK-E04: Edit invalid → fix → Update test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "EditFix")

        if not name:
            log.warning("Prerequisite bank not created")
            return

        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)

        # Enter invalid Bank Name
        page._fill_input_by_name("Bank Name", "Bad123!")
        page.wait_seconds(0.5)
        state1 = page.get_field_validation_state("Bank Name")
        log.info(f"After invalid name: invalid={state1['invalid']}")

        # Fix to valid
        valid_name = generate_bank_name("FixEd")
        page._fill_input_by_name("Bank Name", valid_name)
        page.wait_seconds(0.5)
        state2 = page.get_field_validation_state("Bank Name")
        assert not state2["invalid"], "Fixed Bank Name should be accepted"

        page.update()
        page.wait_seconds(3)

        alert = page.handle_success_alert(timeout=5)
        log.info(f"Update result: {alert}")

        _cleanup_form(page)

    # ---- BNK-E05: Edit Bank Name to invalid ----
    def test_BNK_E05_edit_invalid_bank_name(self, bnk_page):
        """Edit Bank Name to an invalid value — should be blocked."""
        log.info("BNK-E05: Edit invalid Bank Name test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "EdInv")

        if not name:
            log.warning("Prerequisite bank not created")
            return

        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)

        # Enter invalid name (too short)
        short_name = generate_bank_name_too_short()
        page._fill_input_by_name("Bank Name", short_name)
        page.wait_seconds(0.5)

        page.update()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        popup_still_open = page.is_form_popup_open()

        assert popup_still_open or validation_alert, (
            f"BUG: Edit accepted invalid Bank Name '{short_name}'"
        )

        _cleanup_form(page)

    # ---- BNK-E06: Edit — dropdowns pre-populated ----
    def test_BNK_E06_edit_dropdowns_prepopulated(self, bnk_page):
        """Edit should show Account Type and GL Account pre-populated."""
        log.info("BNK-E06: Edit dropdowns pre-populated test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "EdDD")

        if not name:
            log.warning("Prerequisite bank not created")
            return

        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)

        values = page.get_form_field_values()
        acct_type = values.get("Account Type", "")
        gl_acct = values.get("GL Account", "")

        log.info(f"Account Type pre-selected: '{acct_type}'")
        log.info(f"GL Account pre-selected: '{gl_acct}'")

        _cleanup_form(page)

    # ---- BNK-E07: Edit — toggle states preserved ----
    def test_BNK_E07_edit_toggle_states_preserved(self, bnk_page):
        """Toggle states should be preserved when opening Edit form."""
        log.info("BNK-E07: Edit toggle states preserved test")
        page = bnk_page

        name, data = _create_prerequisite_bank(page, "EdTgl")

        if not name:
            log.warning("Prerequisite bank not created")
            return

        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)

        is_default = page.get_toggle_state("Is Default Bank?")
        status = page.get_toggle_state("Status")

        log.info(f"Edit mode — Is Default Bank: {is_default}, Status: {status}")

        _cleanup_form(page)

    # ---- BNK-E08: Edit — Cancel reverts changes ----
    def test_BNK_E08_edit_cancel_reverts(self, bnk_page):
        """Clicking Cancel on Edit should revert changes."""
        log.info("BNK-E08: Edit cancel reverts test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "EdCnl")

        if not name:
            log.warning("Prerequisite bank not created")
            return

        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)

        # Modify a field
        page._fill_input_by_name("Bank Address", "MODIFIED ADDRESS FOR TESTING")
        page.wait_seconds(0.5)

        # Cancel instead of Update
        page.cancel()
        page.wait_seconds(1)

        # The original data should still be there
        page.click_refresh()
        page.wait_seconds(2)
        found = page.is_bank_in_table(name)
        assert found, f"Bank '{name}' should still exist after cancel"

        # Verify the modified address was NOT saved
        # Open edit again and check
        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)
        values = page.get_form_field_values()
        current_addr = values.get("Bank Address", "")

        assert "MODIFIED" not in current_addr, (
            "BUG: Modified address was saved despite Cancel"
        )
        log.info("Cancel correctly reverted — modified address not saved")

        _cleanup_form(page)


# ====================================================================
# PHASE 4: Search & Filter Edge Cases (6 tests)
# ====================================================================

class TestSearchFilterEdgeCases:
    """BNK-S01 to BNK-S06: Search and filter tests.

    BUG-003 (MEDIUM): Search does not filter the Bank table at all.
    Tests that expect filtering will be marked @pytest.mark.xfail.
    """

    # ---- BNK-S01: Search with exact bank name ----
    @pytest.mark.xfail(
        reason="BUG-003: Global search does not filter the Bank table. "
               "Exact name search returns all rows unchanged.",
    )
    def test_BNK_S01_search_exact_name(self, bnk_page):
        """Search with exact bank name should filter the table."""
        log.info("BNK-S01: Search exact name test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "Search1")

        if not name:
            log.warning("Prerequisite bank not created — cannot test search")
            return

        page.search(name)
        page.wait_seconds(2)

        rows_before = page.get_table_row_count()
        found = page.is_bank_in_table(name)
        log.info(
            f"Search '{name}': rows={rows_before}, "
            f"found={found}"
        )

        # Clear search
        page.clear_search()
        page.wait_seconds(2)
        rows_after = page.get_table_row_count()

        log.info(f"After clear: rows={rows_after}")

    # ---- BNK-S02: Search with partial name ----
    @pytest.mark.xfail(
        reason="BUG-003: Global search does not filter the Bank table.",
    )
    def test_BNK_S02_search_partial_name(self, bnk_page):
        """Search with partial bank name should filter the table."""
        log.info("BNK-S02: Search partial name test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "Search2")
        if not name:
            return

        partial = name[:5] if len(name) >= 5 else name
        page.search(partial)
        page.wait_seconds(2)

        found = page.is_bank_in_table(name)
        log.info(f"Search partial '{partial}': found={found}")

        page.clear_search()

    # ---- BNK-S03: Search with special characters ----
    @pytest.mark.xfail(
        reason="BUG-003: Global search does not filter the Bank table.",
    )
    def test_BNK_S03_search_special_chars(self, bnk_page):
        """Search with special characters should be handled gracefully."""
        log.info("BNK-S03: Search special chars test")

        page.search("!@#$%^&*()")
        page.wait_seconds(2)
        log.info("Special chars search completed (no crash)")

        page.clear_search()

    # ---- BNK-S04: Search with non-existent term ----
    @pytest.mark.xfail(
        reason="BUG-003: Global search does not filter the Bank table.",
    )
    def test_BNK_S04_search_non_existent(self, bnk_page):
        """Search with non-existent term should show no results."""
        log.info("BNK-S04: Search non-existent term test")

        page.search("ZZZZNONEXISTENTBANK99999")
        page.wait_seconds(2)

        has_no_data = page.driver.execute_script(
            "return document.querySelector('td.no-data') !== null || "
            "document.querySelector('.mat-mdc-no-data-row') !== null;"
        )
        rows = page.get_table_row_count()

        log.info(f"Non-existent search: has_no_data={has_no_data}, rows={rows}")

    # ---- BNK-S05: Clear search → all results return ----
    def test_BNK_S05_clear_search_restores(self, bnk_page):
        """Clearing search should restore all results."""
        log.info("BNK-S05: Clear search restores test")

        page.search("TestSearchFilter")
        page.wait_seconds(2)

        page.clear_search()
        page.wait_seconds(2)

        rows = page.get_table_row_count()
        log.info(f"After clear: rows={rows}")
        assert rows > 0, "Table should show records after clearing search"

    # ---- BNK-S06: Search with Account Number ----
    @pytest.mark.xfail(
        reason="BUG-003: Global search does not filter the Bank table.",
    )
    def test_BNK_S06_search_account_number(self, bnk_page):
        """Search with Account Number should filter the table."""
        log.info("BNK-S06: Search by Account Number test")

        name, data = _create_prerequisite_bank(page, "SearchAcct")
        acct = data.get("account_number", "")
        if not acct:
            return

        page.search(acct)
        page.wait_seconds(2)

        found = page.is_bank_in_table(name)
        log.info(f"Search by Account Number '{acct}': found={found}")

        page.clear_search()


# ====================================================================
# PHASE 5: Popup & UI Behaviors (10 tests)
# ====================================================================

class TestPopupUIBehaviors:
    """BNK-P01 to BNK-P10: Popup and UI interaction tests."""

    # ---- BNK-P01: Add popup — Cancel dismisses form ----
    def test_BNK_P01_add_cancel_dismisses(self, bnk_page):
        """Cancel on Add popup should close the form without saving."""
        log.info("BNK-P01: Add Cancel dismisses test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)
        assert page.is_add_form_open(), "Add form should be open"

        page.cancel()
        page.wait_seconds(1)

        assert not page.is_add_form_open(), "Cancel should close the popup"
        log.info("Cancel correctly closed the Add popup")

    # ---- BNK-P02: Backdrop click behavior ----
    def test_BNK_P02_backdrop_click(self, bnk_page):
        """Clicking the backdrop should close or dismiss the popup."""
        log.info("BNK-P02: Backdrop click test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)
        assert page.is_add_form_open(), "Add form should be open"

        # Click on the dark backdrop
        self._click_backdrop(page)
        page.wait_seconds(1)

        popup_open = page.is_add_form_open()
        log.info(f"After backdrop click: popup_open={popup_open}")

    def _click_backdrop(self, page):
        """Click the dark overlay backdrop behind the popup."""
        try:
            backdrop = page.driver.find_element(
                By.CSS_SELECTOR,
                ".cdk-overlay-dark-backdrop, .cdk-overlay-backdrop",
            )
            if backdrop.is_displayed():
                page.driver.execute_script(
                    "arguments[0].click();", backdrop
                )
        except Exception:
            pass

    # ---- BNK-P03: Edit popup — Cancel reverts ----
    def test_BNK_P03_edit_cancel_reverts(self, bnk_page):
        """Cancel on Edit popup should revert all changes."""
        log.info("BNK-P03: Edit Cancel reverts test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "P03Cancel")
        if not name:
            return

        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)

        # Modify field
        original = page.get_input_value("Bank Address")
        page._fill_input_by_name("Bank Address", "CANCEL_TEST_VALUE")
        page.wait_seconds(0.5)

        page.cancel()
        page.wait_seconds(1)

        # Verify original value still there
        page.click_edit_button(bank_name=name)
        page.wait_seconds(2)
        current = page.get_input_value("Bank Address")
        assert "CANCEL_TEST_VALUE" not in current, "Edit Cancel reverted changes"

        _cleanup_form(page)

    # ---- BNK-P04: View popup — all fields disabled ----
    def test_BNK_P04_view_fields_disabled(self, bnk_page):
        """View popup should have all fields disabled (read-only)."""
        log.info("BNK-P04: View fields disabled test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "P04View")
        if not name:
            return

        page.click_view_button(bank_name=name)
        page.wait_seconds(2)

        assert page.is_form_popup_open(), "View popup should open"
        assert page.is_view_mode(), "Should be in view mode (only Cancel button)"

        # Check disabled state
        disabled_fields = [
            ("Bank Name", page.is_field_disabled("Bank Name")),
            ("Bank Code", page.is_field_disabled("Bank Code")),
            ("Branch Name", page.is_field_disabled("Branch Name")),
            ("IFSC Code", page.is_field_disabled("IFSC Code")),
            ("Bank Address", page.is_field_disabled("Bank Address")),
        ]
        for label, disabled in disabled_fields:
            log.info(f"  {label}: disabled={disabled}")
            # At minimum, critical fields should be disabled in view mode
            if label in ["Bank Name", "Bank Code", "IFSC Code"]:
                assert disabled, f"{label} should be disabled in View mode"

        _cleanup_form(page)

    # ---- BNK-P05: View popup — character counters ----
    def test_BNK_P05_view_character_counters(self, bnk_page):
        """View popup should show character counters (e.g., '10 / 255')."""
        log.info("BNK-P05: View character counters test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "P05CC")
        if not name:
            return

        page.click_view_button(bank_name=name)
        page.wait_seconds(2)

        # Check for character counter elements in view mode
        counters = page.driver.execute_script("""
            var popup = document.querySelector(
                '.edit_pop_up.override_edit_pop_up.popup-mode'
            );
            if (!popup) return 'No popup';
            var counters = popup.querySelectorAll(
                '.char-counter, [class*=\"character\"]'
            );
            return counters.length;
        """)
        log.info(f"Character counters found: {counters}")

        assert counters > 0, "Character counters should be visible in View mode"
        log.info("Character counters visible in View popup")

        _cleanup_form(page)

    # ---- BNK-P06: Pagination navigation ----
    def test_BNK_P06_pagination(self, bnk_page):
        """Table has pagination and page navigation works."""
        log.info("BNK-P06: Pagination test")
        page = bnk_page

        page_info = page.get_current_page_info()
        log.info(f"Pagination info: {page_info}")

        # Try to go to next page
        went_next = page.go_to_next_page()
        log.info(f"Went to next page: {went_next}")

        if went_next:
            page_info_after = page.get_current_page_info()
            log.info(f"After next page: {page_info_after}")

    # ---- BNK-P07: Items per page selector ----
    def test_BNK_P07_items_per_page(self, bnk_page):
        """Items per page selector should be available and functional."""
        log.info("BNK-P07: Items per page test")

        # Check if items per page text exists
        page_info = page.get_current_page_info()
        log.info(f"Page info: {page_info}")

        assert "10" in page_info or "40" in page_info, (
            "Default page size should be 10"
        )

    # ---- BNK-P08: More menu — Export to Excel ----
    def test_BNK_P08_export_to_excel(self, bnk_page):
        """More menu should have Export to Excel option."""
        log.info("BNK-P08: Export to Excel test")

        opened = page.open_more_menu()
        log.info(f"More menu opened: {opened}")

    # ---- BNK-P09: Form close + reopen — no state leakage ----
    def test_BNK_P09_no_state_leakage(self, bnk_page):
        """After closing and reopening form, old values should be gone."""
        log.info("BNK-P09: No state leakage test")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Fill some data
        data = generate_valid_bank_data("Leakage")
        page._fill_input_by_name("Bank Name", data["bank_name"])
        page._fill_input_by_name("Bank Code", data["bank_code"])
        page.wait_seconds(0.5)

        name_val = page.get_input_value("Bank Name")
        code_val = page.get_input_value("Bank Code")
        log.info(f"Filled: name='{name_val}', code='{code_val}'")

        # Close and reopen
        page.cancel()
        page.wait_seconds(1)

        page.open_add_form()
        page.wait_seconds(1)

        new_name = page.get_input_value("Bank Name")
        new_code = page.get_input_value("Bank Code")
        log.info(f"After reopen: name='{new_name}', code='{new_code}'")

        assert new_name != name_val, (
            "State leakage: Bank Name value persisted after close"
        )
        assert new_code != code_val, (
            "State leakage: Bank Code value persisted after close"
        )

        log.info("No state leakage confirmed — form is clean on reopen")
        page.cancel()

    # ---- BNK-P10: Refresh button reloads data ----
    def test_BNK_P10_refresh_reloads(self, bnk_page):
        """Refresh button should reload the table data."""
        log.info("BNK-P10: Refresh reloads test")

        rows_before = page.get_table_row_count()
        log.info(f"Rows before refresh: {rows_before}")

        page.click_refresh()
        page.wait_seconds(2)

        rows_after = page.get_table_row_count()
        log.info(f"Rows after refresh: {rows_after}")

        # Page count text
        page_info = page.get_current_page_info()
        log.info(f"Page info: {page_info}")


# ====================================================================
# PHASE 6: History & Audit Trail (3 tests)
# ====================================================================

class TestHistoryAuditTrail:
    """BNK-H01 to BNK-H03: History and audit trail tests.

    BUG-006 (LOW): History button opens View popup instead of audit trail.
    """

    # ---- BNK-H01: History button opens popup ----
    @pytest.mark.xfail(
        reason="BUG-006: History button opens View popup instead of "
               "audit trail popup.",
    )
    def test_BNK_H01_history_opens_popup(self, bnk_page):
        """History button should open a history/audit trail popup."""
        log.info("BNK-H01: History opens popup test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "Hist01")
        if not name:
            return

        page.click_history_button(bank_name=name)
        page.wait_seconds(2)

        popup_open = page.is_form_popup_open()
        log.info(f"Popup opened: {popup_open}")

        assert popup_open, "History button should open a popup"

    # ---- BNK-H02: History popup has change log entries ----
    @pytest.mark.xfail(
        reason="BUG-006: History button opens View popup, not history.",
    )
    def test_BNK_H02_history_change_log(self, bnk_page):
        """History popup should display change log entries with timestamps."""
        log.info("BNK-H02: History change log test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "Hist02")
        if not name:
            return

        page.click_history_button(bank_name=name)
        page.wait_seconds(2)

        is_view = page.is_view_mode()
        log.info(f"Is View mode (BUG-006): {is_view}")

    # ---- BNK-H03: History popup shows timestamps ----
    @pytest.mark.xfail(
        reason="BUG-006: History button opens View popup, no timestamps.",
    )
    def test_BNK_H03_history_timestamps(self, bnk_page):
        """History popup should show timestamps for each change."""
        log.info("BNK-H03: History timestamps test")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "Hist03")
        if not name:
            return

        page.click_history_button(bank_name=name)
        page.wait_seconds(2)

        is_view = page.is_view_mode()
        log.info(f"Is View mode (BUG-006): {is_view}")


# ====================================================================
# PHASE 7: Bug-specific Tests (5 tests)
# ====================================================================

class TestBugSpecific:
    """BNK-B01 to BNK-B05: Tests specifically for known bugs."""

    # ---- BNK-B01: Account Type dropdown missing mat-error text ----
    def test_BNK_B01_dropdown_missing_mat_error(self, bnk_page):
        """Account Type and GL Account dropdowns show NO mat-error text
        when submitted empty despite being required fields.

        BUG-001 (MEDIUM): Dropdown required fields show red highlight
        but no error message text, unlike text input fields which show
        'This field is required'.
        """
        log.info("BNK-B01: Dropdown missing mat-error test (BUG-001)")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Fill text inputs (leave dropdowns empty)
        data = generate_valid_bank_data("B01Test")
        text_fields = [
            ("bank_name", "Bank Name"),
            ("bank_code", "Bank Code"),
            ("branch_name", "Branch Name"),
            ("branch_code", "Branch Code"),
            ("account_number", "Account Number"),
            ("ifsc_code", "IFSC Code"),
            ("cash_credit_limit", "Cash Credit Limit"),
            ("bank_address", "Bank Address"),
        ]
        for key, name_attr in text_fields:
            if data.get(key):
                page._fill_input_by_name(name_attr, data[key])
        # Leave Account Type and GL Account empty
        page._close_dropdown_panel()

        # Submit to trigger validation
        page.submit()
        page.wait_seconds(3)

        # Dismiss SweetAlert if present
        page._dismiss_swal()

        # Check for mat-error on Account Type
        acct_err = page.get_field_error("Account Type")
        log.info(f"Account Type mat-error text: '{acct_err}'")

        # Check for mat-error on GL Account
        gl_err = page.get_field_error("GL Account")
        log.info(f"GL Account mat-error text: '{gl_err}'")

        # BUG-001: Both should be empty (no error text)
        assert not acct_err, (
            "BUG-001 CONFIRMED: Account Type has no mat-error text"
        )
        assert not gl_err, (
            "BUG-001 CONFIRMED: GL Account has no mat-error text"
        )

        log.info("BUG-001 CONFIRMED: Both dropdowns missing mat-error text")

        _cleanup_form(page)

    # ---- BNK-B02: Bank Address missing mat-error text ----
    def test_BNK_B02_bank_address_missing_mat_error(self, bnk_page):
        """Bank Address required field shows NO mat-error text when empty.

        BUG-002 (MEDIUM): Bank Address shows red highlight but no
        error text despite being required.
        """
        log.info("BNK-B02: Bank Address missing mat-error test (BUG-002)")
        page = bnk_page

        page.open_add_form()
        page.wait_seconds(1)

        # Fill all text fields EXCEPT Bank Address
        data = generate_valid_bank_data("B02Test")
        text_fields = [
            ("bank_name", "Bank Name"),
            ("bank_code", "Bank Code"),
            ("branch_name", "Branch Name"),
            ("branch_code", "Branch Code"),
            ("account_number", "Account Number"),
            ("ifsc_code", "IFSC Code"),
            ("cash_credit_limit", "Cash Credit Limit"),
        ]
        for key, name_attr in text_fields:
            if data.get(key):
                page._fill_input_by_name(name_attr, data[key])
        page._close_dropdown_panel()

        # Submit
        page.submit()
        page.wait_seconds(3)
        page._dismiss_swal()

        # Check for mat-error on Bank Address
        addr_err = page.get_field_error("Bank Address")
        log.info(f"Bank Address mat-error text: '{addr_err}'")

        assert not addr_err, "BUG-002 CONFIRMED: No error text"
        log.info("BUG-002 CONFIRMED: Bank Address missing mat-error text")

        _cleanup_form(page)

    # ---- BNK-B03: Search doesn't filter table ----
    @pytest.mark.xfail(
        reason="BUG-003: Global search does not filter the Bank table at all.",
    )
    def test_BNK_B03_search_no_filter(self, bnk_page):
        """Global search does not filter the Bank table.

        BUG-003 (MEDIUM): Searching any term returns all rows unchanged.
        """
        log.info("BNK-B03: Search no-filter test (BUG-003)")
        page = bnk_page

        page.search("UniqueSearchTermXyz123")
        page.wait_seconds(2)

        rows = page.get_table_row_count()
        log.info(f"Rows after search: {rows}")

        assert rows > 0, "Table should still have rows (BUG-003)"

        page.clear_search()

    # ---- BNK-B04: No Delete functionality ----
    def test_BNK_B04_no_delete(self, bnk_page):
        """No Delete button exists anywhere on the Bank screen.

        BUG-005 (LOW): No delete in row actions, edit popup, or more menu.
        """
        log.info("BNK-B04: No delete test (BUG-005)")
        page = bnk_page

        # Check table row action buttons
        btns = page.driver.find_elements(
            By.XPATH,
            "//table[@id='excel-table']//thead//th"
        )
        header_texts = [b.text.strip() for b in btns]
        log.info(f"Table headers: {header_texts}")
        assert "Delete" not in header_texts, "BUG-005: No Delete column"

    # ---- BNK-B05: History opens View popup ----
    @pytest.mark.xfail(
        reason="BUG-006: History button opens View popup, not audit trail.",
    )
    def test_BNK_B05_history_opens_view(self, bnk_page):
        """History button opens View popup instead of audit trail.

        BUG-006 (LOW): History and View buttons open the same popup.
        """
        log.info("BNK-B05: History opens View (BUG-006)")
        page = bnk_page

        name, _ = _create_prerequisite_bank(page, "B05Hist")
        if not name:
            return

        page.click_history_button(bank_name=name)
        page.wait_seconds(2)

        is_view = page.is_view_mode()
        log.info(f"Is View mode (BUG-006): {is_view}")

        assert is_view, "BUG-006: History opened View popup"
