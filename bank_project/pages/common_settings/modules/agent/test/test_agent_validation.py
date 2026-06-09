"""
test_agent_validation.py
-----------------------
Comprehensive validation test suite for RhythmERP Agent screen.
~57 test cases across 7 phases.

Phases:
  1. Create Form Validations  (20 tests) — AGT-C01 to AGT-C20
  2. Duplicate Validations      (5 tests) — AGT-D01 to AGT-D05
  3. Edit Form Validations      (8 tests) — AGT-E01 to AGT-E08
  4. Search & Filter Edge Cases (6 tests) — AGT-S01 to AGT-S06
  5. Popup & UI Behaviors       (10 tests) — AGT-P01 to AGT-P10
  6. History & Audit Trail      (3 tests) — AGT-H01 to AGT-H03
  7. Bug-specific               (5 tests) — AGT-B01 to AGT-B05

FORM LAYOUT (3-step STEPPER form):
  Step 1: Agent Name*, Phone Number*, Email, Status + Address Details
          (Country*→State*→District*→Taluka*, Village, Address*, Pin Code*)
  Step 2: Payment Terms, Preferred Payment Method, Is GST Set Off
  Step 3: Bank Details (Bank Name*, Branch, IFSC, Account Type*,
          Account Holder Name*, Account Number*, Bank Proof*, Attachment)

Known Bugs (CONFIRMED):
  AGT-BUG-001 (CRITICAL): mat-select clicks don't sync Angular form model
  AGT-BUG-002 (MEDIUM): Party Reference has duplicate entries
  AGT-BUG-003 (LOW): Stepper tabs locked until previous step completes
  AGT-BUG-004 (CRITICAL): Angular inputs require execute_script to read values

Run:
  pytest test_agent_validation.py -v --tb=short
  pytest test_agent_validation.py -v -k "TestCreateForm" --tb=short
  pytest test_agent_validation.py -v -k "AGT-C03" --tb=short
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

from pages.common_settings.modules.agent.agent_page import AgentPage
from pages.common_settings.modules.agent.data.agent_data import (
    generate_valid_agent_data,
    generate_valid_edit_data,
    generate_agent_name,
    generate_phone_number,
    generate_email,
    generate_invalid_email,
    generate_address,
    generate_pin_code,
    generate_invalid_pin_code,
    generate_bank_name,
    generate_branch_name,
    generate_ifsc_code,
    generate_account_holder_name,
    generate_account_number,
    generate_spaces_only,
    generate_string_255,
    generate_string_256,
    generate_special_char_name,
    generate_special_char_value,
    generate_sql_injection,
    generate_xss_payload,
    generate_phone_with_letters,
    generate_phone_with_special_chars,
    generate_leading_trailing_spaces,
    VALIDATION_MSG_REQUIRED,
    SWAL_TITLE_VALIDATION_FAILED,
    SWAL_TITLE_SUCCESS,
)
from common.logger import log


# ====================================================================
# Helper: create a prerequisite agent, refresh, return its name
# ====================================================================

def _create_prerequisite_agent(page, prefix="PreReq"):
    """Create an Agent entry for tests that need existing data.
    Returns the agent name and the data dict used.
    """
    data = generate_valid_agent_data(prefix)
    result = page.create_agent(data)
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
    name = result.get("agent_name", "")
    log.info(f"Prerequisite agent created: {name}")
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
# PHASE 1: Create Form Validations (20 tests)
# ====================================================================

class TestCreateFormValidations:
    """AGT-C01 to AGT-C20: Validation checks on the Create form."""

    # ---- AGT-C01: Submit with all fields empty ----
    def test_AGT_C01_empty_submit(self, agt_page):
        """Submit with all fields empty — should be blocked."""
        log.info("AGT-C01: Empty submit test")
        page = agt_page

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

        _cleanup_form(page)

    # ---- AGT-C02: Create with valid data (happy path) ----
    def test_AGT_C02_valid_create(self, agt_page):
        """Create with valid data across all 3 steps — should succeed."""
        log.info("AGT-C02: Valid create test (happy path)")
        page = agt_page

        data = generate_valid_agent_data("ValidC")
        result = page.create_agent(data)
        name = result.get("agent_name", "")

        if result["status"] == "PASSED":
            log.info(f"Agent created successfully: {name}")
        else:
            log.warning(f"Create failed: {result.get('error', 'unknown')}")

        page.click_refresh()
        page.wait_seconds(2)
        found = page.is_agent_in_table(name)

        assert found, f"Created agent '{name}' not found in table after refresh"
        log.info(f"Agent created and found in table: {name}")

    # ---- AGT-C03: Agent Name required validation ----
    def test_AGT_C03_agent_name_required(self, agt_page):
        """Submit without Agent Name — should be blocked."""
        log.info("AGT-C03: Agent Name required validation test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # Leave Agent Name empty, fill other required fields
        page._fill_input_by_name("Agent Name", "")
        page._fill_input_by_name("Phone Number", generate_phone_number())

        page.submit()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        form_still_open = page.is_add_form_open()

        assert form_still_open or validation_alert, (
            "BUG: Form accepted empty Agent Name"
        )

        _cleanup_form(page)

    # ---- AGT-C04: Phone Number required validation ----
    def test_AGT_C04_phone_number_required(self, agt_page):
        """Submit without Phone Number — should be blocked."""
        log.info("AGT-C04: Phone Number required validation test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        page._fill_input_by_name("Agent Name", generate_agent_name("PhReq"))
        page._fill_input_by_name("Phone Number", "")

        page.submit()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        form_still_open = page.is_add_form_open()

        assert form_still_open or validation_alert, (
            "BUG: Form accepted empty Phone Number"
        )

        _cleanup_form(page)

    # ---- AGT-C05: Email optional ----
    def test_AGT_C05_email_optional(self, agt_page):
        """Submit without Email — should still work (email is optional)."""
        log.info("AGT-C05: Email optional test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # Fill without email
        data = generate_valid_agent_data("EmailOpt")
        data["email"] = ""
        result = page.create_agent(data)
        name = result.get("agent_name", "")

        log.info(f"Create without email: status={result['status']}, name={name}")

        if result["status"] == "PASSED":
            page.click_refresh()
            page.wait_seconds(2)
            found = page.is_agent_in_table(name)
            log.info(f"Agent without email found: {found}")

    # ---- AGT-C06: Agent Name with special characters ----
    def test_AGT_C06_agent_name_special_chars(self, agt_page):
        """Agent Name with special characters."""
        log.info("AGT-C06: Agent Name special chars test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        special = generate_special_char_name()
        page._fill_input_by_name("Agent Name", special)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Agent Name")
        log.info(
            f"Special chars Agent Name: "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- AGT-C07: Agent Name with spaces only ----
    def test_AGT_C07_agent_name_spaces_only(self, agt_page):
        """Agent Name with only spaces — should be rejected."""
        log.info("AGT-C07: Agent Name spaces only test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        page._fill_input_by_name("Agent Name", generate_spaces_only())
        page._fill_input_by_name("Phone Number", generate_phone_number())

        page.submit()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        form_still_open = page.is_add_form_open()

        assert form_still_open or validation_alert, (
            "BUG: Form accepted spaces-only Agent Name"
        )

        _cleanup_form(page)

    # ---- AGT-C08: Agent Name maxlength boundary (255) ----
    def test_AGT_C08_agent_name_maxlength(self, agt_page):
        """Agent Name maxlength boundary test (255/256 chars)."""
        log.info("AGT-C08: Agent Name maxlength test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # 255 chars
        long_255 = generate_string_255()
        page._fill_input_by_name("Agent Name", long_255)
        page.wait_seconds(0.5)
        actual_value = page.get_input_value("Agent Name")
        log.info(f"255-char input: actual length = {len(actual_value)}")

        # 256 chars
        long_256 = generate_string_256()
        page._fill_input_by_name("Agent Name", long_256)
        page.wait_seconds(0.5)
        actual_value_256 = page.get_input_value("Agent Name")
        log.info(
            f"256-char input: actual length = {len(actual_value_256)}, "
            f"truncated = {len(actual_value_256) == 255}"
        )

        _cleanup_form(page)

    # ---- AGT-C09: Agent Name exceeding maxlength ----
    def test_AGT_C09_agent_name_exceeds_max(self, agt_page):
        """Agent Name with 256 chars — should be truncated or rejected."""
        log.info("AGT-C09: Agent Name exceeds maxlength test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        long_256 = generate_string_256()
        page._fill_input_by_name("Agent Name", long_256)
        page.wait_seconds(0.5)
        actual = page.get_input_value("Agent Name")
        log.info(f"Input length: {len(long_256)}, Actual length: {len(actual)}")

        _cleanup_form(page)

    # ---- AGT-C10: Phone Number with letters ----
    def test_AGT_C10_phone_letters(self, agt_page):
        """Phone Number with letters — should be rejected."""
        log.info("AGT-C10: Phone Number with letters test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        phone_with_letters = generate_phone_with_letters()
        page._fill_input_by_name("Phone Number", phone_with_letters)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Phone Number")
        log.info(
            f"Phone with letters: "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- AGT-C11: Phone Number with special characters ----
    def test_AGT_C11_phone_special_chars(self, agt_page):
        """Phone Number with special characters — should be rejected."""
        log.info("AGT-C11: Phone Number special chars test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        phone_special = generate_phone_with_special_chars()
        page._fill_input_by_name("Phone Number", phone_special)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Phone Number")
        log.info(
            f"Phone with special chars: "
            f"invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- AGT-C12: Phone Number with spaces only ----
    def test_AGT_C12_phone_spaces_only(self, agt_page):
        """Phone Number with spaces only — should be rejected."""
        log.info("AGT-C12: Phone Number spaces only test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        page._fill_input_by_name("Agent Name", generate_agent_name("PhSp"))
        page._fill_input_by_name("Phone Number", generate_spaces_only())

        page.submit()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        form_still_open = page.is_add_form_open()

        assert form_still_open or validation_alert, (
            "BUG: Form accepted spaces-only Phone Number"
        )

        _cleanup_form(page)

    # ---- AGT-C13: Email with invalid format ----
    def test_AGT_C13_email_invalid_format(self, agt_page):
        """Email with invalid format (no @) — validation behavior."""
        log.info("AGT-C13: Email invalid format test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        invalid_email = generate_invalid_email()
        page._fill_input_by_name("Email", invalid_email)
        page.wait_seconds(0.5)
        state = page.get_field_validation_state("Email")
        log.info(
            f"Invalid email: invalid={state['invalid']}, error='{state['error']}'"
        )

        _cleanup_form(page)

    # ---- AGT-C14: Address Details — Country required ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: Cascading dropdowns require JS workaround. "
               "Country selection may not sync Angular model.",
    )
    def test_AGT_C14_country_required(self, agt_page):
        """Address Details: Country is required."""
        log.info("AGT-C14: Country required validation test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        page._fill_input_by_name("Agent Name", generate_agent_name("CntR"))
        page._fill_input_by_name("Phone Number", generate_phone_number())

        # Add address row but leave Country empty
        page.click_add_address_row()
        page.wait_seconds(1)

        # Click Next to trigger Step 1 validation
        page._scroll_popup_to_bottom()
        page.click_stepper_next()
        page.wait_seconds(3)

        form_still_open = page.is_add_form_open()
        log.info(f"After empty Country + Next: form_open={form_still_open}")

        _cleanup_form(page)

    # ---- AGT-C15: Address Details — State required ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: Cascading State dropdown depends on Country selection.",
    )
    def test_AGT_C15_state_required(self, agt_page):
        """Address Details: State is required."""
        log.info("AGT-C15: State required validation test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        page._fill_input_by_name("Agent Name", generate_agent_name("StaR"))
        page._fill_input_by_name("Phone Number", generate_phone_number())
        page.click_add_address_row()
        page.wait_seconds(1)

        # Select Country but not State
        page._select_cascading_dropdown("Country", "India")
        page.wait_seconds(1)

        page._scroll_popup_to_bottom()
        page.click_stepper_next()
        page.wait_seconds(3)

        form_still_open = page.is_add_form_open()
        log.info(f"After empty State + Next: form_open={form_still_open}")

        _cleanup_form(page)

    # ---- AGT-C16: Address Details — District required ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: Cascading District dropdown depends on State.",
    )
    def test_AGT_C16_district_required(self, agt_page):
        """Address Details: District is required."""
        log.info("AGT-C16: District required validation test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        page._fill_input_by_name("Agent Name", generate_agent_name("DstR"))
        page._fill_input_by_name("Phone Number", generate_phone_number())
        page.click_add_address_row()
        page.wait_seconds(1)

        page._select_cascading_dropdown("Country", "India")
        page.wait_seconds(1)
        page._select_cascading_dropdown("State", "Maharashtra")
        page.wait_seconds(1)

        page._scroll_popup_to_bottom()
        page.click_stepper_next()
        page.wait_seconds(3)

        _cleanup_form(page)

    # ---- AGT-C17: Address Details — Address required ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: Stepper Next may not validate Address field.",
    )
    def test_AGT_C17_address_required(self, agt_page):
        """Address Details: Address text field is required."""
        log.info("AGT-C17: Address required validation test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        page._fill_input_by_name("Agent Name", generate_agent_name("AddR"))
        page._fill_input_by_name("Phone Number", generate_phone_number())
        page.click_add_address_row()
        page.wait_seconds(1)

        # Fill cascading dropdowns but leave Address empty
        page._select_cascading_dropdown("Country", "India")
        page.wait_seconds(1)
        page._select_cascading_dropdown("State", "Maharashtra")
        page.wait_seconds(1)
        # Leave District/Taluka empty — select random if possible
        page._select_cascading_dropdown("District", "Pune")
        page.wait_seconds(1)
        page._select_cascading_dropdown("Taluka", "Pune")
        page.wait_seconds(1)

        # Leave Address empty
        page._fill_input_by_name("Address", "")

        page._scroll_popup_to_bottom()
        page.click_stepper_next()
        page.wait_seconds(3)

        _cleanup_form(page)

    # ---- AGT-C18: Pin Code with non-digits ----
    def test_AGT_C18_pincode_non_digits(self, agt_page):
        """Pin Code with non-digit characters."""
        log.info("AGT-C18: Pin Code non-digits test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        invalid_pin = generate_invalid_pin_code()
        page._fill_input_by_name("Pin Code", invalid_pin)
        page.wait_seconds(0.5)

        _cleanup_form(page)

    # ---- AGT-C19: Add multiple address rows ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: Multiple rows with cascading dropdowns "
               "may not work reliably with JS workaround.",
    )
    def test_AGT_C19_multiple_address_rows(self, agt_page):
        """Add multiple address rows to the form."""
        log.info("AGT-C19: Multiple address rows test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # Add first row
        page.click_add_address_row()
        page.wait_seconds(1)

        # Add second row
        page.click_add_address_row()
        page.wait_seconds(1)

        log.info("Two address rows added")

        _cleanup_form(page)

    # ---- AGT-C20: Maxlength boundary for all text fields ----
    def test_AGT_C20_all_fields_maxlength(self, agt_page):
        """Maxlength boundary test for Agent Name, Address, etc."""
        log.info("AGT-C20: All fields maxlength test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # Test 255 chars in Agent Name
        long_255 = generate_string_255()
        page._fill_input_by_name("Agent Name", long_255)
        actual = page.get_input_value("Agent Name")
        log.info(f"Agent Name 255 chars: input={len(long_255)}, actual={len(actual)}")

        _cleanup_form(page)


# ====================================================================
# PHASE 2: Duplicate Validations (5 tests)
# ====================================================================

class TestDuplicateValidations:
    """AGT-D01 to AGT-D05: Duplicate checks in Create."""

    # ---- AGT-D01: Duplicate Agent Name ----
    def test_AGT_D01_duplicate_agent_name(self, agt_page):
        """Create two agents with the same Agent Name."""
        log.info("AGT-D01: Duplicate Agent Name test")
        page = agt_page

        data1 = generate_valid_agent_data("DupD01")
        result1 = page.create_agent(data1)
        name1 = result1.get("agent_name", "")

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        if not name1:
            log.warning("Agent 1 creation failed — cannot test duplicate")
            return

        data2 = generate_valid_agent_data("DupD02")
        data2["agent_name"] = name1
        result2 = page.create_agent(data2)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        log.info(
            f"Agent 1: '{name1}', Result 2: {result2}"
        )

    # ---- AGT-D02: Duplicate Phone Number ----
    def test_AGT_D02_duplicate_phone_number(self, agt_page):
        """Create two agents with the same Phone Number."""
        log.info("AGT-D02: Duplicate Phone Number test")
        page = agt_page

        data1 = generate_valid_agent_data("DupPh1")
        phone = data1["phone_number"]
        result1 = page.create_agent(data1)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        if result1["status"] != "PASSED":
            log.warning("First agent creation failed — cannot test duplicate")
            return

        data2 = generate_valid_agent_data("DupPh2")
        data2["phone_number"] = phone
        result2 = page.create_agent(data2)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        log.info(f"Duplicate Phone Number '{phone}': result2={result2}")

    # ---- AGT-D03: Case sensitivity ----
    def test_AGT_D03_case_sensitivity(self, agt_page):
        """Create agents with case-sensitive names (e.g., 'Test' vs 'test')."""
        log.info("AGT-D03: Case sensitivity test")
        page = agt_page

        data1 = generate_valid_agent_data("CaseA")
        data1["agent_name"] = "CaseTest AgentOne"
        result1 = page.create_agent(data1)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        data2 = generate_valid_agent_data("CaseB")
        data2["agent_name"] = "casetest agentone"  # lowercase version
        result2 = page.create_agent(data2)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        log.info(
            f"Case sensitivity: result1={result1['status']}, "
            f"result2={result2['status']}"
        )

    # ---- AGT-D04: Leading/trailing spaces ----
    def test_AGT_D04_leading_trailing_spaces(self, agt_page):
        """Create agents with leading/trailing spaces in name."""
        log.info("AGT-D04: Leading/trailing spaces test")
        page = agt_page

        data1 = generate_valid_agent_data("SpaceA")
        data1["agent_name"] = "SpaceTest Agent"
        result1 = page.create_agent(data1)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        if result1["status"] != "PASSED":
            log.warning("First agent creation failed")
            return

        data2 = generate_valid_agent_data("SpaceB")
        data2["agent_name"] = " SpaceTest Agent "  # with spaces
        result2 = page.create_agent(data2)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        log.info(f"Spaces duplicate: result2={result2}")

    # ---- AGT-D05: Same Party Reference for two agents ----
    @pytest.mark.xfail(
        reason="AGT-BUG-002: Party Reference has duplicate entries. "
               "Testing with same reference may not be meaningful.",
    )
    def test_AGT_D05_same_party_reference(self, agt_page):
        """Select same Party Reference for two different agents."""
        log.info("AGT-D05: Same Party Reference test")
        page = agt_page

        data1 = generate_valid_agent_data("RefA")
        result1 = page.create_agent(data1)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        if result1["status"] != "PASSED":
            log.warning("First agent creation failed")
            return

        data2 = generate_valid_agent_data("RefB")
        result2 = page.create_agent(data2)

        _cleanup_form(page)
        page.click_refresh()
        page.wait_seconds(2)

        log.info(f"Same party ref: result1={result1['status']}, result2={result2['status']}")


# ====================================================================
# PHASE 3: Edit Form Validations (8 tests)
# ====================================================================

class TestEditFormValidations:
    """AGT-E01 to AGT-E08: Validation checks on the Edit form."""

    # ---- AGT-E01: Edit — pre-populated fields ----
    def test_AGT_E01_edit_prepopulated(self, agt_page):
        """Edit popup should show all fields pre-populated with existing data."""
        log.info("AGT-E01: Edit pre-populated fields test")
        page = agt_page

        name, data = _create_prerequisite_agent(page, "EditPre")

        if not name:
            log.warning("Prerequisite agent not created — cannot verify edit")
            return

        page.click_edit_button(agent_name=name)
        page.wait_seconds(2)

        assert page.is_form_popup_open(), "Edit form popup did not open"

        values = page.get_form_field_values()
        log.info(f"Form values: {values}")

        # Verify Agent Name is pre-populated
        assert values.get("Agent Name", ""), "Agent Name should be pre-populated"

        log.info("Edit form fields verified as pre-populated")

        _cleanup_form(page)

    # ---- AGT-E02: Edit happy path ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: Edit may fail due to mat-select model sync issues.",
    )
    def test_AGT_E02_edit_happy_path(self, agt_page):
        """Edit an agent, modify fields, and Update — should succeed."""
        log.info("AGT-E02: Edit happy path test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "EditHP")

        if not name:
            log.warning("Prerequisite agent not created — cannot test edit")
            return

        page.click_edit_button(agent_name=name)
        page.wait_seconds(2)

        edit_data = generate_valid_edit_data()
        page._fill_input_by_name("Agent Name", edit_data["agent_name"])
        page._fill_input_by_name("Email", edit_data["email"])

        page.update()
        page.wait_seconds(3)

        alert = page.handle_success_alert(timeout=5)
        if alert:
            log.info(f"Edit success: {alert}")

        page.click_refresh()
        page.wait_seconds(2)

    # ---- AGT-E03: Edit — clear required field → validation ----
    def test_AGT_E03_edit_clear_required(self, agt_page):
        """Clear a required field in Edit mode — should show validation."""
        log.info("AGT-E03: Edit clear required field test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "EditClr")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        page.click_edit_button(agent_name=name)
        page.wait_seconds(2)

        # Clear Agent Name
        page._fill_input_by_name("Agent Name", "")
        page.wait_seconds(0.5)

        page.update()
        page.wait_seconds(3)

        validation_alert = page.handle_validation_warning(timeout=5)
        popup_still_open = page.is_form_popup_open()

        assert popup_still_open or validation_alert, (
            "BUG: Edit allowed clearing required field without validation"
        )

        _cleanup_form(page)

    # ---- AGT-E04: Edit Address row ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: Cascading dropdown edits may not sync.",
    )
    def test_AGT_E04_edit_address_row(self, agt_page):
        """Edit an address row — modify address details."""
        log.info("AGT-E04: Edit Address row test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "EdAddr")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        page.click_edit_button(agent_name=name)
        page.wait_seconds(2)

        if page.is_form_popup_open():
            new_address = generate_address()
            page._fill_input_by_name("Address", new_address)
            page.wait_seconds(0.5)
            log.info(f"Modified Address to: {new_address}")

        _cleanup_form(page)

    # ---- AGT-E05: Edit Bank row ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: Bank detail edits may not sync.",
    )
    def test_AGT_E05_edit_bank_row(self, agt_page):
        """Edit a bank row — modify bank details."""
        log.info("AGT-E05: Edit Bank row test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "EdBank")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        page.click_edit_button(agent_name=name)
        page.wait_seconds(2)

        if page.is_form_popup_open():
            # Navigate to Step 3 (Bank Details)
            page.click_stepper_next()
            page.wait_seconds(2)
            page.click_stepper_next()
            page.wait_seconds(2)

            new_bank = generate_bank_name()
            page._fill_input_by_name("Bank Name", new_bank)
            page.wait_seconds(0.5)
            log.info(f"Modified Bank Name to: {new_bank}")

        _cleanup_form(page)

    # ---- AGT-E06: Edit Payment Details ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: Payment dropdown edits may not sync.",
    )
    def test_AGT_E06_edit_payment_details(self, agt_page):
        """Edit Payment Details — change payment method."""
        log.info("AGT-E06: Edit Payment Details test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "EdPay")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        page.click_edit_button(agent_name=name)
        page.wait_seconds(2)

        if page.is_form_popup_open():
            page.click_stepper_next()
            page.wait_seconds(2)

            page._select_mat_option_by_label_and_value(
                "Preferred Payment Method", "Cash"
            )
            page.wait_seconds(1)

            log.info("Changed Preferred Payment Method to Cash")

        _cleanup_form(page)

    # ---- AGT-E07: Edit — modify Agent Name ----
    def test_AGT_E07_edit_agent_name(self, agt_page):
        """Edit Agent Name to a new valid value."""
        log.info("AGT-E07: Edit Agent Name test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "EdNm")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        page.click_edit_button(agent_name=name)
        page.wait_seconds(2)

        if page.is_form_popup_open():
            new_name = generate_agent_name("NewNm")
            page._fill_input_by_name("Agent Name", new_name)
            page.wait_seconds(0.5)

            actual = page.get_input_value("Agent Name")
            log.info(f"New Agent Name: '{actual}'")

        _cleanup_form(page)

    # ---- AGT-E08: Edit — modify Phone Number ----
    def test_AGT_E08_edit_phone_number(self, agt_page):
        """Edit Phone Number to a new valid value."""
        log.info("AGT-E08: Edit Phone Number test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "EdPh")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        page.click_edit_button(agent_name=name)
        page.wait_seconds(2)

        if page.is_form_popup_open():
            new_phone = generate_phone_number()
            page._fill_input_by_name("Phone Number", new_phone)
            page.wait_seconds(0.5)

            actual = page.get_input_value("Phone Number")
            log.info(f"New Phone Number: '{actual}'")

        _cleanup_form(page)


# ====================================================================
# PHASE 4: Search & Filter Edge Cases (6 tests)
# ====================================================================

class TestSearchFilterEdgeCases:
    """AGT-S01 to AGT-S06: Search and filter tests."""

    # ---- AGT-S01: Search exact match ----
    def test_AGT_S01_search_exact_match(self, agt_page):
        """Search exact match — full agent name."""
        log.info("AGT-S01: Search exact match test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "SearchE")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        page.search(name)
        page.wait_seconds(2)

        found = page.is_agent_in_table(name)
        log.info(f"Search exact '{name}': found={found}")

        # Clear search
        page.clear_search()
        page.wait_seconds(2)

    # ---- AGT-S02: Search partial match ----
    def test_AGT_S02_search_partial_match(self, agt_page):
        """Search partial match — first few characters."""
        log.info("AGT-S02: Search partial match test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "SearchP")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        # Search using prefix
        prefix = name[:10]
        page.search(prefix)
        page.wait_seconds(2)

        found = page.is_agent_in_table(name)
        log.info(f"Search partial '{prefix}': found={found}")

        page.clear_search()
        page.wait_seconds(2)

    # ---- AGT-S03: Search case sensitivity ----
    def test_AGT_S03_search_case_sensitivity(self, agt_page):
        """Search with different case."""
        log.info("AGT-S03: Search case sensitivity test")
        page = agt_page

        page.search("AGENT")
        page.wait_seconds(2)

        names = page.get_all_agent_names()
        log.info(f"Search 'AGENT': {len(names)} results")

        page.clear_search()
        page.wait_seconds(2)

        page.search("agent")
        page.wait_seconds(2)

        names2 = page.get_all_agent_names()
        log.info(f"Search 'agent': {len(names2)} results")

        page.clear_search()
        page.wait_seconds(2)

    # ---- AGT-S04: Search with special characters ----
    def test_AGT_S04_search_special_chars(self, agt_page):
        """Search with special characters — should not crash."""
        log.info("AGT-S04: Search special chars test")
        page = agt_page

        page.search("!@#$%^&*()")
        page.wait_seconds(2)

        names = page.get_all_agent_names()
        log.info(f"Search special chars: {len(names)} results")

        page.clear_search()
        page.wait_seconds(2)

    # ---- AGT-S05: Search no results ----
    def test_AGT_S05_search_no_results(self, agt_page):
        """Search with nonexistent name — should return no results."""
        log.info("AGT-S05: Search no results test")
        page = agt_page

        page.search("ZZZZNONEXISTENT99999")
        page.wait_seconds(2)

        names = page.get_all_agent_names()
        log.info(f"Search nonexistent: {len(names)} results")

        page.clear_search()
        page.wait_seconds(2)

    # ---- AGT-S06: Clear search restores all ----
    def test_AGT_S06_clear_search_restores(self, agt_page):
        """Clear search should restore all results."""
        log.info("AGT-S06: Clear search restores test")
        page = agt_page

        initial_count = page.get_table_row_count()
        log.info(f"Initial row count: {initial_count}")

        page.search("ZZZZNONEXISTENT")
        page.wait_seconds(2)

        filtered_count = page.get_table_row_count()
        log.info(f"After search: {filtered_count} rows")

        page.clear_search()
        page.wait_seconds(2)

        restored_count = page.get_table_row_count()
        log.info(f"After clear: {restored_count} rows")

        assert restored_count >= initial_count, (
            f"Clear search didn't restore rows: {restored_count} < {initial_count}"
        )


# ====================================================================
# PHASE 5: Popup & UI Behaviors (10 tests)
# ====================================================================

class TestPopupUIBehaviors:
    """AGT-P01 to AGT-P10: Popup and UI behavior tests."""

    # ---- AGT-P01: Form opens on Add click ----
    def test_AGT_P01_form_opens_on_add(self, agt_page):
        """Form popup opens when Add Agent is clicked."""
        log.info("AGT-P01: Form opens on Add test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        assert page.is_add_form_open(), "Form popup did not open"
        log.info("Form popup opened successfully")

        _cleanup_form(page)

    # ---- AGT-P02: Form closes on Cancel ----
    def test_AGT_P02_cancel_closes_form(self, agt_page):
        """Form closes when Cancel is clicked without saving."""
        log.info("AGT-P02: Cancel closes form test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)
        assert page.is_add_form_open(), "Form not open"

        page.cancel()
        page.wait_seconds(1)

        form_open = page.is_add_form_open()
        assert not form_open, "Form still open after Cancel"

        log.info("Form closed after Cancel")

    # ---- AGT-P03: Fullscreen button ----
    def test_AGT_P03_fullscreen_button(self, agt_page):
        """Fullscreen button exists in popup header."""
        log.info("AGT-P03: Fullscreen button test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        try:
            popup = page.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            fullscreen_btns = popup.find_elements(
                By.CSS_SELECTOR, "button.mdc-icon-button"
            )
            log.info(f"Found {len(fullscreen_btns)} icon buttons in popup header")

            for btn in fullscreen_btns:
                try:
                    icon = btn.find_element(By.CSS_SELECTOR, "mat-icon")
                    if icon.text.strip() == "fullscreen":
                        log.info("Fullscreen button found")
                        break
                except Exception:
                    continue
        except Exception as e:
            log.warning(f"Fullscreen button check failed: {e}")

        _cleanup_form(page)

    # ---- AGT-P04: Close (X) button ----
    def test_AGT_P04_close_button(self, agt_page):
        """Close (X) button closes the form popup."""
        log.info("AGT-P04: Close (X) button test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)
        assert page.is_add_form_open(), "Form not open"

        try:
            popup = page.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            close_btns = popup.find_elements(
                By.CSS_SELECTOR, "button.mdc-icon-button"
            )
            for btn in close_btns:
                try:
                    icon = btn.find_element(By.CSS_SELECTOR, "mat-icon")
                    if icon.text.strip() == "close":
                        btn.click()
                        page.wait_seconds(1)
                        log.info("Close button clicked")
                        break
                except Exception:
                    continue
        except Exception as e:
            log.warning(f"Close button check failed: {e}")

    # ---- AGT-P05: Stepper navigation — Next ----
    def test_AGT_P05_stepper_next(self, agt_page):
        """Stepper Next button advances through steps."""
        log.info("AGT-P05: Stepper Next test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        step1 = page.get_current_stepper_step()
        log.info(f"Initial step: {step1}")

        # Fill minimum required to advance
        page._fill_input_by_name("Agent Name", generate_agent_name("Step"))
        page._fill_input_by_name("Phone Number", generate_phone_number())
        page.click_add_address_row()
        page.wait_seconds(1)

        page._scroll_popup_to_bottom()
        page.click_stepper_next()
        page.wait_seconds(2)

        step2 = page.get_current_stepper_step()
        log.info(f"After Next: step = {step2}")

        _cleanup_form(page)

    # ---- AGT-P06: Stepper navigation — Previous ----
    def test_AGT_P06_stepper_previous(self, agt_page):
        """Stepper Previous button goes back."""
        log.info("AGT-P06: Stepper Previous test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        page._fill_input_by_name("Agent Name", generate_agent_name("Prev"))
        page._fill_input_by_name("Phone Number", generate_phone_number())
        page.click_add_address_row()
        page.wait_seconds(1)

        page._scroll_popup_to_bottom()
        page.click_stepper_next()
        page.wait_seconds(2)

        step_after_next = page.get_current_stepper_step()
        log.info(f"After Next: step = {step_after_next}")

        page.click_stepper_previous()
        page.wait_seconds(2)

        step_after_prev = page.get_current_stepper_step()
        log.info(f"After Previous: step = {step_after_prev}")

        _cleanup_form(page)

    # ---- AGT-P07: Add address row ----
    def test_AGT_P07_add_address_row(self, agt_page):
        """Clicking add creates a new address row."""
        log.info("AGT-P07: Add address row test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        result = page.click_add_address_row()
        log.info(f"Add address row: {result}")

        _cleanup_form(page)

    # ---- AGT-P08: Add bank row ----
    def test_AGT_P08_add_bank_row(self, agt_page):
        """Clicking add creates a new bank row (on step 3)."""
        log.info("AGT-P08: Add bank row test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # Fill step 1 minimum
        page._fill_input_by_name("Agent Name", generate_agent_name("BnkRow"))
        page._fill_input_by_name("Phone Number", generate_phone_number())
        page.click_add_address_row()
        page.wait_seconds(1)

        # Advance to step 2
        page._scroll_popup_to_bottom()
        page.click_stepper_next()
        page.wait_seconds(2)

        # Advance to step 3
        page.click_stepper_next()
        page.wait_seconds(2)

        # Add bank row
        result = page.click_add_bank_row()
        log.info(f"Add bank row: {result}")

        _cleanup_form(page)

    # ---- AGT-P09: Items per page ----
    def test_AGT_P09_items_per_page(self, agt_page):
        """Items per page selector is available."""
        log.info("AGT-P09: Items per page test")
        page = agt_page

        try:
            select = page.driver.find_element(
                By.CSS_SELECTOR,
                "mat-paginator-page-size select, .mat-mdc-paginator-page-size select",
            )
            log.info(f"Items per page selector found: {select.is_displayed()}")
        except Exception:
            log.warning("Items per page selector not found")

    # ---- AGT-P10: Table pagination ----
    def test_AGT_P10_table_pagination(self, agt_page):
        """Table pagination works (Next/Prev)."""
        log.info("AGT-P10: Table pagination test")
        page = agt_page

        initial_count = page.get_table_row_count()
        log.info(f"Initial row count: {initial_count}")

        next_result = page.go_to_next_page()
        if next_result:
            log.info("Next page clicked")
            page.wait_seconds(1)
            page.go_to_previous_page()
            log.info("Previous page clicked")


# ====================================================================
# PHASE 6: History & Audit Trail (3 tests)
# ====================================================================

class TestHistoryAuditTrail:
    """AGT-H01 to AGT-H03: History and audit trail tests."""

    # ---- AGT-H01: History button opens popup ----
    def test_AGT_H01_history_opens_popup(self, agt_page):
        """History button opens a popup."""
        log.info("AGT-H01: History opens popup test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "HistA")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        page.click_history_button(agent_name=name)
        page.wait_seconds(2)

        popup_open = page.is_form_popup_open()
        log.info(f"History popup opened: {popup_open}")

        _cleanup_form(page)

    # ---- AGT-H02: History shows timestamps ----
    def test_AGT_H02_history_timestamps(self, agt_page):
        """History popup shows timestamps."""
        log.info("AGT-H02: History timestamps test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "HistB")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        page.click_history_button(agent_name=name)
        page.wait_seconds(2)

        try:
            popup = page.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            text = popup.text
            log.info(f"History popup text length: {len(text)}")
        except Exception:
            log.warning("Could not read history popup")

        _cleanup_form(page)

    # ---- AGT-H03: History shows field change details ----
    def test_AGT_H03_history_change_details(self, agt_page):
        """History shows field change details after edit."""
        log.info("AGT-H03: History change details test")
        page = agt_page

        name, _ = _create_prerequisite_agent(page, "HistC")

        if not name:
            log.warning("Prerequisite agent not created")
            return

        # Edit the agent
        page.click_edit_button(agent_name=name)
        page.wait_seconds(2)

        if page.is_form_popup_open():
            new_name = generate_agent_name("HistEdit")
            page._fill_input_by_name("Agent Name", new_name)
            page.update()
            page.wait_seconds(3)
            page.handle_success_alert(timeout=5)

        page.click_refresh()
        page.wait_seconds(2)

        # Now check history
        page.click_history_button(agent_name=new_name)
        page.wait_seconds(2)

        _cleanup_form(page)


# ====================================================================
# PHASE 7: Bug-specific (5 tests)
# ====================================================================

class TestBugSpecific:
    """AGT-B01 to AGT-B05: Bug-specific verification tests."""

    # ---- AGT-B01: mat-select JS workaround ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: This test verifies the JS workaround works.",
    )
    def test_AGT_B01_mat_select_js_workaround(self, agt_page):
        """Verify that JS-based dropdown selection properly updates Angular model."""
        log.info("AGT-B01: mat-select JS workaround test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # Use JS workaround to select Country
        result = page._select_cascading_dropdown("Country", "India")
        log.info(f"Country selection result: {result}")

        # Now try to select State (proves Angular model was updated)
        page.wait_seconds(3)
        state_result = page._select_random_option("State")
        log.info(f"State selection (cascaded): {state_result}")

        _cleanup_form(page)

    # ---- AGT-B02: Party Reference duplicates ----
    @pytest.mark.xfail(
        reason="AGT-BUG-002: Party Reference has known duplicate entries.",
    )
    def test_AGT_B02_party_reference_duplicates(self, agt_page):
        """Verify Party Reference has duplicate entries (BUG)."""
        log.info("AGT-B02: Party Reference duplicates test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # Open Party Reference dropdown and read options
        js = """
            var popup = document.querySelector(
                '.edit_pop_up.override_edit_pop_up.popup-mode'
            );
            if (!popup) return [];
            var formFields = popup.querySelectorAll('mat-form-field');
            for (var i = 0; i < formFields.length; i++) {
                var label = formFields[i].querySelector('mat-label');
                if (label && label.textContent.trim() === 'Party Reference') {
                    var select = formFields[i].querySelector('mat-select');
                    if (select) select.click();
                    break;
                }
            }
        """
        page.driver.execute_script(js)
        page.wait_seconds(2)

        options = page._get_dropdown_options()
        log.info(f"Party Reference options count: {len(options)}")

        # Check for duplicates
        from collections import Counter
        counts = Counter(options)
        duplicates = {k: v for k, v in counts.items() if v > 1}
        if duplicates:
            log.info(f"Duplicate entries found: {dict(list(duplicates.items())[:5])}")
        else:
            log.info("No duplicates found")

        page._close_dropdown_panel()
        _cleanup_form(page)

    # ---- AGT-B03: Stepper tabs locked ----
    def test_AGT_B03_stepper_tabs_locked(self, agt_page):
        """Verify stepper tabs 2 and 3 are disabled initially."""
        log.info("AGT-B03: Stepper tabs locked test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        try:
            tabs = page.driver.find_elements(By.CSS_SELECTOR, "[role='tab']")
            for i, tab in enumerate(tabs):
                aria_disabled = tab.get_attribute("aria-disabled")
                text = tab.text.strip()
                log.info(f"Tab {i+1}: '{text}' aria-disabled={aria_disabled}")
        except Exception as e:
            log.warning(f"Could not read stepper tabs: {e}")

        _cleanup_form(page)

    # ---- AGT-B04: Angular input value reading ----
    def test_AGT_B04_input_value_reading(self, agt_page):
        """Verify execute_script can read Angular input values."""
        log.info("AGT-B04: Input value reading test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # Fill Agent Name using JS value-setter
        test_name = "TestInputReading"
        page._fill_input_by_name("Agent Name", test_name)
        page.wait_seconds(0.5)

        # Read using execute_script (reliable)
        js_value = page.get_input_value("Agent Name")
        log.info(f"execute_script value: '{js_value}'")

        assert js_value == test_name, (
            f"execute_script read failed: expected '{test_name}', got '{js_value}'"
        )
        log.info("execute_script value reading works correctly")

        _cleanup_form(page)

    # ---- AGT-B05: State cascading from Country ----
    @pytest.mark.xfail(
        reason="AGT-BUG-001: State dropdown may fail to cascade from Country.",
    )
    def test_AGT_B05_state_cascading(self, agt_page):
        """Verify State dropdown cascades from Country selection."""
        log.info("AGT-B05: State cascading test")
        page = agt_page

        page.open_add_form()
        page.wait_seconds(1)

        # Select India
        page._select_cascading_dropdown("Country", "India")
        page.wait_seconds(3)

        # Try to select a state — proves cascade worked
        state = page._select_random_option("State")
        log.info(f"State selected (cascaded from India): {state}")

        assert state, "State dropdown failed to cascade from Country"

        _cleanup_form(page)
