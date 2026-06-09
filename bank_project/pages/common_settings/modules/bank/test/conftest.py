"""
conftest.py - Bank Common Settings (RhythmERP)
"""

import os
import sys
import logging
import pytest

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

from common.logger import log
from common.browser_utils import get_driver
from pages.login_screens.Login_Screens_.login_page import LoginPage
from common.screenshot_broadcast import start as start_screenshot_broadcast, stop as stop_screenshot_broadcast
from config import RHYTHMERP_LOGIN_URL, RHYTHMERP_EMAIL, RHYTHMERP_PASSWORD
from pages.common_settings.cs_report_generator import (
    CSReportStore,
    generate_cs_report,
)


# ================================================================
# FIXTURES
# ================================================================

@pytest.fixture(scope="session")
def driver():
    log.separator()
    log.info("LAUNCHING BROWSER (RhythmERP - Bank Tests)...")
    log.separator()
    drv = get_driver()
    drv.maximize_window()
    yield drv
    log.separator()
    log.info("CLOSING BROWSER...")
    log.separator()
    try:
        drv.quit()
    except Exception:
        pass


@pytest.fixture(scope="session")
def logged_in_driver(driver):
    """Driver with completed RhythmERP login session."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    log.separator()
    log.info("LOGGING INTO RHYTHMERP...")
    log.separator()

    login_page = LoginPage(driver)

    log.info("Navigating to: " + str(RHYTHMERP_LOGIN_URL))
    driver.get(RHYTHMERP_LOGIN_URL)
    login_page.wait_seconds(3)

    log.step(1, "Entering email: " + str(RHYTHMERP_EMAIL))
    login_page.enter_email(RHYTHMERP_EMAIL)

    log.step(2, "Entering password")
    login_page.enter_password(RHYTHMERP_PASSWORD)

    log.step(3, "Selecting facility (blank - first option)")
    login_page.select_facility_by_index(index=0)

    # Wait for facility overlay to fully close
    login_page.wait_seconds(2)

    log.step(4, "Clicking Login button")
    # Use WebDriverWait for presence (not clickable — Angular may keep it "not clickable")
    # then ActionChains for the actual click.
    submit_btn = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']"))
    )
    ActionChains(driver).move_to_element(submit_btn).click().perform()
    login_page.wait_seconds(5)

    login_page.wait_for_login_complete(timeout=30)
    log.info("RhythmERP login successful!")

    try:
        start_screenshot_broadcast(driver)
    except Exception:
        pass

    yield driver

    try:
        stop_screenshot_broadcast()
    except Exception:
        pass


@pytest.fixture
def bnk_page(logged_in_driver):
    """Bank page object — fresh navigation for each test."""
    from pages.common_settings.modules.bank.bank_page import BankPage
    page = BankPage(logged_in_driver)
    page.navigate_to_page()
    yield page


# ================================================================
# REPORT GENERATOR HOOKS
# ================================================================

_bnk_store = CSReportStore()

# ---- Bank Known Issues ----

# BUG-001 (MEDIUM): Required dropdown fields missing mat-error text
_bnk_store.record_issue(
    severity="Medium",
    module="Bank",
    category="Missing Validation",
    description="Account Type and GL Account dropdowns show NO mat-error text when "
                "submitted empty. The fields get a red highlight (ng-invalid) but no "
                "descriptive error message is displayed. Unlike text inputs that show "
                "'This field is required', dropdowns silently fail without telling the "
                "user what's wrong.",
    expected="mat-error text like 'This field is required' should appear below "
             "each dropdown field, consistent with text input behavior.",
    actual="CONFIRMED: Red highlight only, no error text for Account Type or "
           "GL Account on empty submit.",
    test_ref="BNK-B01",
    status="Confirmed",
)

# BUG-002 (MEDIUM): Bank Address required field missing mat-error text
_bnk_store.record_issue(
    severity="Medium",
    module="Bank",
    category="Missing Validation",
    description="Bank Address is marked as required (has asterisk) and is blocked "
                "on empty submit, but no mat-error text is displayed. The field appears "
                "invalid but gives the user no feedback about what's wrong.",
    expected="mat-error text 'This field is required' should appear below the field.",
    actual="CONFIRMED: Red highlight only, no error text for Bank Address.",
    test_ref="BNK-B02",
    status="Confirmed",
)

# BUG-003 (MEDIUM): Global search does not filter the Bank table
_bnk_store.record_issue(
    severity="Medium",
    module="Bank",
    category="Functionality",
    description="The ERP global search input (placeholder: 'Search anything...') does not "
                "filter the Bank table results. Searching for a specific bank name or a "
                "non-existent term returns all rows unchanged. The search appears completely "
                "disconnected from this dynamic screen.",
    expected="Table should filter to show only matching rows.",
    actual="CONFIRMED: No filtering occurs on any search term. "
           "Typing 'BankZYXWVU' or 'ZZZZNONEXISTENT' both show all 10 rows.",
    test_ref="BNK-B03",
    status="Confirmed",
)

# BUG-004 (CRITICAL): Browser-clicked mat-select does NOT reliably update Angular form
_bnk_store.record_issue(
    severity="Critical",
    module="Bank",
    category="Automation",
    description="Browser-clicked mat-select options do NOT reliably update the Angular "
                "reactive form model. The first dropdown selection in a session may work, "
                "but subsequent selections fail silently. The form model remains empty even "
                "though the UI shows a selected value. Must use JS value-setter + "
                "dispatchEvent for all dropdown selections.",
    expected="Selenium/Playwright clicks on mat-select options should update form state.",
    actual="CONFIRMED: Angular form model not synced. JS workaround required "
           "for reliable dropdown selection.",
    test_ref="ALL",
    status="Confirmed",
)

# BUG-005 (LOW): No Delete functionality
_bnk_store.record_issue(
    severity="Low",
    module="Bank",
    category="Functionality",
    description="No Delete option exists anywhere on the Bank screen. Not in the "
                "table row actions (View/Edit/History), not in the Edit popup, and not "
                "in the more_vert menu (which only has 'Export to Excel'). Records "
                "cannot be removed once created.",
    expected="A Delete option should exist for removing bank records.",
    actual="CONFIRMED: No delete functionality available. Records cannot be removed.",
    test_ref="BNK-B04",
    status="Confirmed",
)

# BUG-006 (LOW): History button opens View popup instead of audit trail
_bnk_store.record_issue(
    severity="Low",
    module="Bank",
    category="UI Bug",
    description="Clicking the 'History' button on a table row opens the same View "
                "popup (read-only form with Cancel button), not a history/audit trail "
                "popup. There is no way to view the change history of a Bank record.",
    expected="Should open a history popup showing change log with timestamps.",
    actual="CONFIRMED: Opens the same View popup as the View button. "
           "No history entries or timestamps visible.",
    test_ref="BNK-B05, BNK-H01",
    status="Confirmed",
)


# ================================================================
# LOG CAPTURE + PYTEST HOOKS
# ================================================================

class _LogCapture(logging.Handler):
    """Captures log messages during each test for step-level reporting."""

    def __init__(self, store):
        super().__init__()
        self.store = store

    def emit(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        self.store.add_log_message(msg)


_capture_handler = None


def pytest_runtest_setup(item):
    """Start log capture before each test."""
    global _capture_handler
    _bnk_store.start_test(item.name, item.nodeid)

    _capture_handler = _LogCapture(_bnk_store)
    _capture_handler.setLevel(logging.INFO)
    try:
        if hasattr(log, "logger") and log.logger:
            log.logger.addHandler(_capture_handler)
        elif hasattr(log, "handlers"):
            log.handlers.append(_capture_handler)
    except Exception:
        logging.getLogger().addHandler(_capture_handler)


def pytest_runtest_teardown(item, nextitem):
    """Detach log handler after each test."""
    global _capture_handler
    if _capture_handler is None:
        return
    try:
        if hasattr(log, "logger") and log.logger:
            log.logger.removeHandler(_capture_handler)
        elif hasattr(log, "handlers") and _capture_handler in log.handlers:
            log.handlers.remove(_capture_handler)
    except Exception:
        pass
    _capture_handler = None


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_makereport(item, call):
    """Capture test result (pass/fail) and finalize for report."""
    outcome = yield
    report = outcome.get_result()
    if call.when == "call":
        if report.passed:
            status = "PASSED"
            error = ""
        elif report.failed:
            status = "FAILED"
            error = str(report.longrepr) if report.longrepr else ""
        else:
            status = "SKIPPED"
            error = ""
        _bnk_store.finish_test(status, error)


def pytest_sessionfinish(session, exitstatus):
    """Generate Excel report at end of test session."""
    if not _bnk_store.has_results():
        return
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "reports"
    )
    try:
        filepath = generate_cs_report(
            _bnk_store.results, output_dir, issues=_bnk_store.known_issues
        )
        print("")
        print("=" * 60)
        print("  REPORT GENERATED: " + filepath)
        print("=" * 60)
    except Exception:
        import traceback as tb
        tb.print_exc()
        print("")
        print("  [WARNING] Report generation failed (see traceback above)")
