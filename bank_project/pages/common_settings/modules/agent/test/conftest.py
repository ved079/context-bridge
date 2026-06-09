"""
conftest.py - Agent Common Settings (RhythmERP)
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
from config import RHYTHMERP_LOGIN_URL
from pages.common_settings.cs_report_generator import (
    CSReportStore,
    generate_cs_report,
)

# Agent screen uses DIFFERENT login credentials
AGENT_EMAIL = "Rular@admin.com"
AGENT_PASSWORD = "Rular@12345678"


# ================================================================
# FIXTURES
# ================================================================

@pytest.fixture(scope="session")
def driver():
    log.separator()
    log.info("LAUNCHING BROWSER (RhythmERP - Agent Tests)...")
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
    """Driver with completed RhythmERP login session (Agent credentials)."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    log.separator()
    log.info("LOGGING INTO RHYTHMERP (Agent credentials)...")
    log.separator()

    login_page = LoginPage(driver)

    log.info("Navigating to: " + str(RHYTHMERP_LOGIN_URL))
    driver.get(RHYTHMERP_LOGIN_URL)
    login_page.wait_seconds(3)

    log.step(1, "Entering email: " + str(AGENT_EMAIL))
    login_page.enter_email(AGENT_EMAIL)

    log.step(2, "Entering password")
    login_page.enter_password(AGENT_PASSWORD)

    log.step(3, "Selecting facility (index 0 — RuralLife Producer Company)")
    login_page.select_facility_by_index(index=0)

    # Wait for facility overlay to fully close
    login_page.wait_seconds(2)

    log.step(4, "Clicking Login button")
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
def agt_page(logged_in_driver):
    """Agent page object — fresh navigation for each test."""
    from pages.common_settings.modules.agent.agent_page import AgentPage
    page = AgentPage(logged_in_driver)
    page.navigate_to_page()
    yield page


# ================================================================
# REPORT GENERATOR HOOKS
# ================================================================

_agt_store = CSReportStore()

# ---- Agent Known Issues ----

# AGT-BUG-001 (CRITICAL): mat-select options don't update Angular form model
_agt_store.record_issue(
    severity="Critical",
    module="Agent",
    category="Automation",
    description="Browser-clicked mat-select options do NOT reliably update "
                "Angular reactive form model. Clicking an option visually "
                "shows the selection but the internal form state is not "
                "updated, breaking cascading dropdowns and form validation. "
                "Affects all dropdowns on all 3 stepper steps.",
    expected="Clicking mat-select options should update the Angular "
             "reactive form model, enabling cascading and validation.",
    actual="CONFIRMED: Country appears selected visually but State "
           "options don't load. Must use JS workaround.",
    test_ref="ALL",
    status="Confirmed",
)

# AGT-BUG-002 (MEDIUM): Party Reference dropdown has duplicate entries
_agt_store.record_issue(
    severity="Medium",
    module="Agent",
    category="Data Integrity",
    description="Party Reference dropdown has duplicate entries "
                "('Zeeshan Joshi' repeated ~46 times at the end) and "
                "invalid entries ('ds&^%##%', 'uytrfsDZfxgchvjb5645'). "
                "Total shows 503 entries.",
    expected="Unique party reference names only. Invalid characters "
             "should be rejected.",
    actual="CONFIRMED: Duplicates and invalid data present in dropdown. "
           "System accepts these values without validation.",
    test_ref="AGT-B02",
    status="Confirmed",
)

# AGT-BUG-003 (LOW): Stepper tabs locked until previous step completes
_agt_store.record_issue(
    severity="Low",
    module="Agent",
    category="UI",
    description="Payment Details and Bank Details stepper tabs are disabled "
                "(aria-disabled='true') until the preceding step is completed. "
                "Cannot freely navigate between steps.",
    expected="All tabs should be clickable for easy navigation.",
    actual="CONFIRMED: Tabs 2 and 3 are disabled until Step 1 is "
           "completed and Next is clicked.",
    test_ref="AGT-B03",
    status="Confirmed",
)

# AGT-BUG-004 (CRITICAL): Angular input values require JS to read
_agt_store.record_issue(
    severity="Critical",
    module="Agent",
    category="Automation",
    description="Angular Material inputs store values in DOM property "
                "(.value) not HTML attribute (getAttribute('value')). "
                "Using get_attribute('value') returns null. Must use "
                "get_property('value') or execute_script.",
    expected="getAttribute('value') should return the actual value.",
    actual="CONFIRMED: Returns null. execute_script with inp.value "
           "used as workaround.",
    test_ref="AGT-B04",
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
    _agt_store.start_test(item.name, item.nodeid)

    _capture_handler = _LogCapture(_agt_store)
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
        _agt_store.finish_test(status, error)


def pytest_sessionfinish(session, exitstatus):
    """Generate Excel report at end of test session."""
    if not _agt_store.has_results():
        return
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "reports"
    )
    try:
        filepath = generate_cs_report(
            _agt_store.results, output_dir, issues=_agt_store.known_issues
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
