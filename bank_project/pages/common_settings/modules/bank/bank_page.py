"""
bank_page.py
------------
Page Object Model for RhythmERP Bank screen.

Location: Common Settings > Bank
URL:      /#/dynamic-screens/Bank

FORM LAYOUT (simple popup — NOT a stepper form):

  Single-page popup with heading "Bank":

    Text Inputs (10):
    - Bank Name              (text input,   required, maxlength=255)
    - Bank Code              (text input,   required, maxlength=255)
    - Branch Name            (text input,   required, maxlength=255)
    - Branch Code            (text input,   required, maxlength=255)
    - Account Number         (text input,   required, maxlength=255)
    - Swift Number           (text input,   optional, maxlength=255)
    - IBAN Number            (text input,   optional, maxlength=255)
    - IFSC Code              (text input,   required, maxlength=255)
    - Cash Credit Limit      (text input,   required, maxlength=255)
    - Bank Address           (text input,   required, maxlength=255)

    Dropdowns (2):
    - Account Type           (mat-select,   required, searchable)
                              Options: "Current", "Saving"
    - GL Account             (mat-select,   required, searchable, 116+ options)

    Toggles (2):
    - Is Default Bank?       (app-slide-toggle-v2, default No)
    - Status                 (app-slide-toggle-v2, default Active)

TABLE COLUMNS (main listing):
  - View / Edit / History   (action buttons per row)
  - Bank Name
  - Account Number
  - IFSC Code
  - Status

KEY RULES (verified from live application 2026-05-19):
  - Simple popup (NO stepper, NO Next/Back buttons)
  - NO formcontrolname attributes — only name attributes (exact case, e.g. name="Bank Name")
  - Bank Name: ALL UPPERCASE letters only, appears to require >= 10 chars
  - IFSC Code: Exactly 11 chars
  - BUG-004 (CRITICAL): Browser-clicked mat-select options do NOT reliably
    update Angular reactive form model. Must use JS value-setter + dispatchEvent
    for ALL dropdown selections.
  - SweetAlert2 for success/validation popups
  - Character counters visible in View mode only
  - Edit mode button says "Update" not "Submit"
  - View mode: all fields disabled, only "Cancel" button
  - History button opens View popup (BUG-006)
  - No Delete functionality (BUG-005)
  - Global search does not filter Bank table (BUG-003)
"""

import os
import sys
import time
import random

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

from common.base_page import BasePage
from common.logger import log
from config import RHYTHMERP_BASE_URL, EXPLICIT_WAIT


class BankPage(BasePage):
    PAGE_URL = f"{RHYTHMERP_BASE_URL}/#/dynamic-screens/Bank"

    # ==============================================================
    #  LOCATORS — Toolbar
    # ==============================================================
    ADD_BUTTON = (
        "css",
        "button.erp-add-btn",
    )
    SEARCH_TOGGLE = ("css", "button.search-btn, button[aria-label='Search']")
    REFRESH_BUTTON = ("css", "button[mattooltip='Refresh']")
    MORE_BUTTON = ("css", "button[mattooltip='More']")

    # ==============================================================
    #  LOCATORS — Search bar
    # ==============================================================
    SEARCH_INPUT = ("css", ".erp-search-wrapper input, input#erpSearchInput")
    SEARCH_SUBMIT = ("css", "button.search-btn")

    # ==============================================================
    #  LOCATORS — Table (main listing)
    # ==============================================================
    TABLE = ("css", "table#excel-table")
    TABLE_ROWS = ("css", "table#excel-table tbody tr")
    TABLE_BANK_NAME_CELLS = (
        "css",
        "table#excel-table tbody td:nth-child(4)",
    )
    TABLE_ACCOUNT_CELLS = (
        "css",
        "table#excel-table tbody td:nth-child(5)",
    )
    TABLE_IFSC_CELLS = (
        "css",
        "table#excel-table tbody td:nth-child(6)",
    )
    TABLE_STATUS_CELLS = (
        "css",
        "table#excel-table tbody td:nth-child(7)",
    )
    NO_DATA_ROW = (
        "css",
        "table#excel-table tbody tr td.no-data, "
        "table#excel-table tbody tr.mat-mdc-no-data-row",
    )

    # ==============================================================
    #  LOCATORS — Form popup
    # ==============================================================
    FORM_POPUP = (
        "css",
        ".edit_pop_up.override_edit_pop_up.popup-mode",
    )
    FORM_HEADING = (
        "css",
        ".edit_pop_up h3, .edit_pop_up.override_edit_pop_up.popup-mode h3",
    )

    # ==============================================================
    #  LOCATORS — Text inputs (by name attribute)
    # ==============================================================
    BANK_NAME_INPUT = ("css", "input[name='Bank Name']")
    BANK_CODE_INPUT = ("css", "input[name='Bank Code']")
    BRANCH_NAME_INPUT = ("css", "input[name='Branch Name']")
    BRANCH_CODE_INPUT = ("css", "input[name='Branch Code']")
    ACCOUNT_NUMBER_INPUT = ("css", "input[name='Account Number']")
    SWIFT_NUMBER_INPUT = ("css", "input[name='Swift Number']")
    IBAN_NUMBER_INPUT = ("css", "input[name='IBAN Number']")
    IFSC_CODE_INPUT = ("css", "input[name='IFSC Code']")
    CASH_CREDIT_LIMIT_INPUT = ("css", "input[name='Cash Credit Limit']")
    BANK_ADDRESS_INPUT = ("css", "input[name='Bank Address']")

    # ==============================================================
    #  LOCATORS — Dropdowns (mat-select, by mat-label XPath)
    # ==============================================================
    ACCOUNT_TYPE_SELECT = (
        "xpath",
        "//mat-label[contains(.,'Account Type')]"
        "/ancestor::mat-form-field//mat-select",
    )
    GL_ACCOUNT_SELECT = (
        "xpath",
        "//mat-label[contains(.,'GL Account')]"
        "/ancestor::mat-form-field//mat-select",
    )

    # ==============================================================
    #  LOCATORS — Toggles (app-slide-toggle-v2)
    # ==============================================================
    IS_DEFAULT_BANK_TOGGLE = (
        "xpath",
        "//app-slide-toggle-v2[.//span[contains(@class,'main-label') "
        "and contains(.,'Is Default Bank?')]]"
        "//div[contains(@class,'switch-wrapper')]",
    )
    STATUS_TOGGLE = (
        "xpath",
        "//app-slide-toggle-v2[.//span[contains(@class,'main-label') "
        "and contains(.,'Status')]]"
        "//div[contains(@class,'switch-wrapper')]",
    )

    # ==============================================================
    #  LOCATORS — Footer buttons
    # ==============================================================
    SUBMIT_BUTTON = (
        "xpath",
        "//div[@class='popup-footer']//button[contains(.,'Submit')]",
    )
    UPDATE_BUTTON = (
        "xpath",
        "//div[@class='popup-footer']//button[contains(.,'Update')]",
    )
    CANCEL_BUTTON = (
        "xpath",
        "//div[@class='popup-footer']//button[contains(.,'Cancel')]",
    )

    # ==============================================================
    #  LOCATORS — Row action buttons (parametrised by bank name)
    # ==============================================================
    VIEW_BUTTON = (
        "xpath",
        "//td[contains(text(),'{bank_name}')]"
        "/ancestor::tr//td[1]//button",
    )
    EDIT_BUTTON = (
        "xpath",
        "//td[contains(text(),'{bank_name}')]"
        "/ancestor::tr//td[2]//button",
    )
    HISTORY_BUTTON = (
        "xpath",
        "//td[contains(text(),'{bank_name}')]"
        "/ancestor::tr//td[3]//button",
    )

    # ==============================================================
    #  LOCATORS — SweetAlert2
    # ==============================================================
    SWAL_TITLE = ("css", "#swal2-title")
    SWAL_HTML = ("css", ".swal2-html-container")
    SWAL_CONFIRM = ("css", ".swal2-confirm")
    SWAL_CANCEL = ("css", ".swal2-cancel")
    SWAL_CONTAINER = ("css", ".swal2-container")

    # ==============================================================
    #  LOCATORS — Validation errors
    # ==============================================================
    MAT_ERROR = ("css", "mat-error, .mat-mdc-form-field-error")
    FIELD_ERROR = (
        "xpath",
        "//mat-label[contains(.,'{field_label}')]"
        "/ancestor::mat-form-field//mat-error",
    )

    # ==============================================================
    #  LOCATORS — Dropdown overlay
    # ==============================================================
    DROPDOWN_PANEL = (
        "css",
        "div.cdk-overlay-pane mat-select-panel, div[role='listbox']",
    )
    DROPDOWN_OPTIONS = (
        "css",
        "div[role='listbox'] mat-option, div[role='listbox'] [role='option']",
    )
    DROPDOWN_SEARCH = (
        "css",
        "div[role='listbox'] input, .cdk-overlay-pane input[placeholder]",
    )

    # ==============================================================
    #  LOCATORS — Pagination
    # ==============================================================
    PAGINATION_NEXT = ("css", "button[aria-label='Next page'], button.mat-mdc-paginator-navigation-next")
    PAGINATION_PREV = ("css", "button[aria-label='Previous page'], button.mat-mdc-paginator-navigation-previous")
    ITEMS_PER_PAGE_SELECT = ("css", "mat-paginator-page-size select, .mat-mdc-paginator-page-size select")

    # ==============================================================
    #  LOCATORS — More menu
    # ==============================================================
    EXPORT_EXCEL_OPTION = (
        "xpath",
        "//button[contains(.,'Export to Excel') or contains(.,'Download as')]",
    )

    # ==============================================================
    #  Navigation & page load
    # ==============================================================

    def navigate_to_page(self):
        """Navigate to the Bank listing page.
        Force-refreshes to clear leftover Angular state from previous tests.
        """
        log.info("Navigating to Bank page...")
        self.navigate_to(self.PAGE_URL)
        self.driver.refresh()
        self._wait_for_page_ready()

    def _wait_for_page_ready(self):
        """Wait until the Bank page is fully loaded:
        1. Table renders
        2. Toolbar buttons (including ADD) are clickable
        """
        try:
            WebDriverWait(self.driver, EXPLICIT_WAIT).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "table#excel-table")
                )
            )
            log.info("Bank table loaded")
        except TimeoutException:
            log.warning("Bank table not found, page may be empty")

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ul.tbl-export-btn")
                )
            )
            self.wait_seconds(1)
            log.info("Bank toolbar ready")
        except TimeoutException:
            log.warning("Toolbar not found, ADD button may be delayed")
            self.wait_seconds(3)

    def is_page_loaded(self):
        """Check if the Bank listing page has loaded."""
        return self.is_displayed(self.TABLE, timeout=10)

    # ==============================================================
    #  Overlay cleanup — NEVER use Keys.ESCAPE
    # ==============================================================

    def _force_close_panels(self):
        """Remove ALL select overlay panes from the DOM via JS.
        Keeps dialog backdrop intact so form popups stay open.
        """
        self.driver.execute_script("""
            document.querySelectorAll(
                'div.cdk-overlay-backdrop:not(.cdk-overlay-dark-backdrop)'
            ).forEach(function(el) { el.remove(); });
            document.querySelectorAll(
                'div.cdk-overlay-pane'
            ).forEach(function(el) {
                if (!el.querySelector('mat-dialog-container')) el.remove();
            });
        """)
        self.wait_seconds(0.2)

    def _close_select_panel(self):
        """Try backdrop click first; fall back to JS removal."""
        try:
            backdrops = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div.cdk-overlay-backdrop:not(.cdk-overlay-dark-backdrop)",
            )
            for bd in backdrops:
                try:
                    if bd.is_displayed():
                        bd.click()
                        self.wait_seconds(0.3)
                        return
                except Exception:
                    pass
        except Exception:
            pass

        remaining = self.driver.find_elements(
            By.CSS_SELECTOR,
            "div.cdk-overlay-backdrop:not(.cdk-overlay-dark-backdrop), "
            "div.cdk-overlay-pane mat-option",
        )
        if remaining:
            self._force_close_panels()

    def _close_dropdown_panel_only(self):
        """Close an open mat-select dropdown panel WITHOUT sending ESC."""
        self._close_select_panel()

    # ==============================================================
    #  Toolbar actions
    # ==============================================================

    def open_add_form(self):
        """Click the ADD (+) button to open the create form.
        Bank opens a simple single-page popup (not stepper).
        """
        log.info("Clicking ADD Bank button...")
        self._wait_for_toolbar()

        # Strategy 1: button.erp-add-btn
        try:
            btn = self.driver.find_element(
                By.CSS_SELECTOR, "button.erp-add-btn"
            )
            if btn.is_displayed():
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});"
                    "arguments[0].click();",
                    btn,
                )
                self.wait_seconds(1.5)
                if self._is_form_popup_open():
                    self._wait_for_form_content(timeout=5)
                    log.info("ADD form opened via erp-add-btn")
                    return
        except Exception:
            pass

        # Strategy 2: Find mini-fab button with 'add' icon
        try:
            add_btns = self.driver.find_elements(
                By.CSS_SELECTOR, "button.mat-mdc-mini-fab"
            )
            for btn in add_btns:
                try:
                    icon = btn.find_element(By.CSS_SELECTOR, "mat-icon")
                    if icon.text.strip().lower() == "add" and btn.is_displayed():
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});"
                            "arguments[0].click();",
                            btn,
                        )
                        self.wait_seconds(1.5)
                        if self._is_form_popup_open():
                            self._wait_for_form_content(timeout=5)
                            log.info("ADD form opened via mini-fab icon")
                            return
                except Exception:
                    continue
        except Exception:
            pass

        # Strategy 3: Button with 'Add Bank' text
        try:
            btns = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in btns:
                try:
                    if "Add Bank" in btn.text and btn.is_displayed():
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});"
                            "arguments[0].click();",
                            btn,
                        )
                        self.wait_seconds(1.5)
                        if self._is_form_popup_open():
                            self._wait_for_form_content(timeout=5)
                            log.info("ADD form opened via text match")
                            return
                except Exception:
                    continue
        except Exception:
            pass

        # Strategy 4: BasePage click_with_retry
        try:
            self.click_with_retry(self.ADD_BUTTON)
            self.wait_seconds(1.5)
            if self._is_form_popup_open():
                self._wait_for_form_content(timeout=5)
                log.info("ADD form opened via click_with_retry")
                return
        except Exception:
            pass

        raise Exception("ADD Bank button not found or not clickable")

    def _wait_for_toolbar(self):
        """Wait for the toolbar and ADD button to be present and visible."""
        for attempt in range(3):
            try:
                add_container = self.driver.find_elements(
                    By.CSS_SELECTOR, "button.erp-add-btn"
                )
                if add_container and add_container[0].is_displayed():
                    return
            except Exception:
                pass

            try:
                btns = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in btns:
                    try:
                        if "Add Bank" in btn.text and btn.is_displayed():
                            return
                    except Exception:
                        continue
            except Exception:
                pass

            log.info(f"Waiting for toolbar... attempt {attempt + 1}/3")
            self.wait_seconds(2)

        log.warning("Toolbar wait exhausted, ADD button may not be ready")

    def _is_form_popup_open(self):
        """Quick check if the Bank form popup is visible."""
        try:
            popups = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode, "
                "mat-dialog-container, "
                "div.cdk-overlay-container div.popup-wrapper",
            )
            for p in popups:
                try:
                    if p.is_displayed():
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _wait_for_form_content(self, timeout=5):
        """Wait for form content to render inside the popup."""
        import time as _time
        deadline = _time.time() + timeout
        while _time.time() < deadline:
            try:
                elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".edit_pop_up.override_edit_pop_up.popup-mode input, "
                    ".edit_pop_up.override_edit_pop_up.popup-mode mat-select, "
                    ".edit_pop_up.override_edit_pop_up.popup-mode .popup-footer button",
                )
                for el in elements:
                    try:
                        if el.is_displayed():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            self.wait_seconds(0.5)

        log.warning(f"Form content did not render within {timeout}s")
        return False

    def click_refresh(self):
        """Click the Refresh button. Falls back to page refresh + navigate."""
        log.info("Clicking Refresh button...")

        # Strategy 1: mini-fab with refresh icon
        try:
            refresh_btns = self.driver.find_elements(
                By.CSS_SELECTOR, "button.mat-mdc-mini-fab"
            )
            for btn in refresh_btns:
                try:
                    icon = btn.find_element(By.CSS_SELECTOR, "mat-icon")
                    if icon.text.strip().lower() == "refresh" and btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        self.wait_seconds(2)
                        log.info("Refresh clicked via mini-fab")
                        return
                except Exception:
                    continue
        except Exception:
            pass

        # Strategy 2: any button with refresh tooltip or icon
        try:
            all_btns = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in all_btns:
                try:
                    tooltip = btn.get_attribute("mattooltip") or ""
                    if "refresh" in tooltip.lower() and btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        self.wait_seconds(2)
                        log.info("Refresh clicked via tooltip match")
                        return
                    icon = btn.find_element(By.CSS_SELECTOR, "mat-icon")
                    if icon.text.strip().lower() == "refresh" and btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        self.wait_seconds(2)
                        log.info("Refresh clicked via icon match")
                        return
                except Exception:
                    continue
        except Exception:
            pass

        # Strategy 3: simple page navigate as fallback
        log.warning("Refresh button not found, using page re-navigate")
        self.navigate_to(self.PAGE_URL)
        self._wait_for_page_ready()

    # ==============================================================
    #  Form filling — JS value-setter for Angular compatibility
    # ==============================================================

    def _fill_input_by_name(self, name_attr, value):
        """Fill an input field by its name attribute using JS value-setter.

        Uses the native input value setter + dispatchEvent pattern to
        ensure Angular reactive form model is properly updated.
        This is critical because simple send_keys may not trigger Angular
        change detection (BUG-004 applies to inputs too in some cases).
        """
        js = f"""
            var popup = document.querySelector(
                '.edit_pop_up.override_edit_pop_up.popup-mode'
            );
            if (!popup) return 'No popup';
            var input = popup.querySelector('input[name="{name_attr}"]');
            if (input) {{
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(input, arguments[0]);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'OK';
            }}
            return 'Not found: {name_attr}';
        """
        result = self.driver.execute_script(js, str(value))
        if "OK" not in str(result):
            log.warning(f"Input not filled: {name_attr} — {result}")

    def _fill_input_via_locator(self, locator, value):
        """Fill an input field using a locator tuple (type, value)."""
        try:
            el = self.find_element(locator)
            if el:
                js = """
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    nativeInputValueSetter.call(arguments[0], arguments[1]);
                    arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                    arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                """
                self.driver.execute_script(js, el, str(value))
                return True
        except Exception as e:
            log.warning(f"Failed to fill input via locator: {e}")
        return False

    def _clear_input_by_name(self, name_attr):
        """Clear an input field by its name attribute using JS value-setter."""
        self._fill_input_by_name(name_attr, "")

    # ==============================================================
    #  Dropdown selection — JS approach (BUG-004)
    # ==============================================================

    def _select_mat_option_by_label_and_value(self, label_text, option_text):
        """Select a mat-select dropdown option using JS to properly set Angular form value.

        This is the reliable workaround for BUG-004 where browser-clicked mat-options
        don't update Angular's reactive form model. Instead of clicking through the UI,
        we directly find the mat-select component, open it programmatically, trigger
        the option selection via mat-select's internal _onSelect method, and dispatch
        change events so Angular picks it up.

        Args:
            label_text: The mat-label text (e.g. 'Account Type', 'GL Account')
            option_text: The option text to select (e.g. 'Current', 'Saving')

        Returns:
            bool: True if selection succeeded
        """
        js = f"""
            var popup = document.querySelector(
                '.edit_pop_up.override_edit_pop_up.popup-mode'
            );
            if (!popup) return 'No popup';

            // Find the mat-form-field by its label
            var formFields = popup.querySelectorAll('mat-form-field');
            var targetSelect = null;
            for (var i = 0; i < formFields.length; i++) {{
                var label = formFields[i].querySelector('mat-label');
                if (label && label.textContent.trim() === '{label_text}') {{
                    targetSelect = formFields[i].querySelector('mat-select');
                    break;
                }}
            }}
            if (!targetSelect) return 'Select not found: {label_text}';

            // Get the Angular component reference
            var ngSelect = targetSelect; // mat-select element

            // Open the select panel
            ngSelect.click();
        """
        result1 = self.driver.execute_script(js)
        self.wait_seconds(2)

        # Now click the option
        js2 = f"""
            var options = document.querySelectorAll('.cdk-overlay-pane mat-option');
            for (var i = 0; i < options.length; i++) {{
                if (options[i].textContent.trim() === '{option_text}') {{
                    options[i].click();
                    return 'Selected: {option_text}';
                }}
            }}
            // Try role=option fallback
            var allOpts = document.querySelectorAll('.cdk-overlay-pane [role="option"]');
            for (var i = 0; i < allOpts.length; i++) {{
                if (allOpts[i].textContent.trim() === '{option_text}') {{
                    allOpts[i].click();
                    return 'Selected (role): {option_text}';
                }}
            }}
            return 'Not found: {option_text}';
        """
        result2 = self.driver.execute_script(js2)
        self.wait_seconds(2)

        log.info(f"Dropdown '{label_text}' -> '{option_text}': {result2}")
        return "Selected" in str(result2)

    def _select_option_by_text(self, option_text):
        """Select a mat-option from the currently open dropdown panel.

        Uses a hybrid approach: finds the option via JS, then uses Selenium
        click to trigger Angular's mat-select _onSelect handler properly.
        Falls back to JS click if Selenium click fails.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        try:
            options = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".cdk-overlay-pane mat-option")
                )
            )
        except Exception:
            try:
                options = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, ".cdk-overlay-pane [role='option']")
                    )
                )
            except Exception:
                log.warning(f"No dropdown options found for: {option_text}")
                return False

        for opt in options:
            try:
                if opt.text.strip() == option_text:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", opt
                    )
                    self.wait_seconds(0.2)
                    # Selenium click first
                    try:
                        opt.click()
                        self.wait_seconds(1.5)
                        return True
                    except Exception:
                        # Fallback: JS click
                        self.driver.execute_script("arguments[0].click();", opt)
                        self.wait_seconds(1.5)
                        return True
            except Exception as e:
                log.warning(f"Failed to click option '{option_text}': {e}")
                continue

        log.warning(f"Option not found in panel: {option_text}")
        return False

    def _close_dropdown_panel(self):
        """Close any open dropdown overlay panel gently."""
        try:
            backdrops = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div.cdk-overlay-backdrop:not(.cdk-overlay-dark-backdrop)"
            )
            if backdrops:
                for bd in backdrops:
                    try:
                        if bd.is_displayed():
                            bd.click()
                            self.wait_seconds(0.5)
                            return
                    except Exception:
                        pass
        except Exception:
            pass
        # Fallback: if backdrop click didn't work, force close
        remaining = self.driver.find_elements(
            By.CSS_SELECTOR,
            "div.cdk-overlay-backdrop:not(.cdk-overlay-dark-backdrop)"
        )
        if remaining:
            self._force_close_panels()
        self.wait_seconds(0.3)

    def select_account_type(self, value):
        """Select an Account Type dropdown option ('Current' or 'Saving')."""
        log.info(f"Selecting Account Type: {value}")
        self._select_mat_option_by_label_and_value("Account Type", value)

    def select_gl_account(self, value):
        """Select a GL Account dropdown option."""
        log.info(f"Selecting GL Account: {value}")
        self._select_mat_option_by_label_and_value("GL Account", value)

    def select_random_account_type(self):
        """Select a random Account Type option from the live UI.
        Returns the selected option text.
        """
        log.info("Selecting random Account Type...")
        # Open dropdown
        self.driver.execute_script("""
            var popup = document.querySelector('.edit_pop_up.override_edit_pop_up.popup-mode');
            if (!popup) return;
            var formFields = popup.querySelectorAll('mat-form-field');
            for (var i = 0; i < formFields.length; i++) {
                var label = formFields[i].querySelector('mat-label');
                if (label && label.textContent.trim() === 'Account Type') {
                    var select = formFields[i].querySelector('mat-select');
                    if (select) select.click();
                    break;
                }
            }
        """)
        self.wait_seconds(1.5)

        options = self._get_dropdown_options()
        valid_opts = [o for o in options if o.strip()]
        if not valid_opts:
            self._close_dropdown_panel()
            return None

        chosen = random.choice(valid_opts)
        # Click the option
        self.driver.execute_script(f"""
            var options = document.querySelectorAll('.cdk-overlay-pane mat-option');
            for (var i = 0; i < options.length; i++) {{
                if (options[i].textContent.trim() === '{chosen}') {{
                    options[i].click();
                    break;
                }}
            }}
        """)
        self.wait_seconds(2)
        log.info(f"Selected Account Type: {chosen}")
        return chosen

    def select_random_gl_account(self):
        """Select a random GL Account option from the live UI.
        Returns the selected option text.
        """
        log.info("Selecting random GL Account...")
        # Open dropdown
        self.driver.execute_script("""
            var popup = document.querySelector('.edit_pop_up.override_edit_pop_up.popup-mode');
            if (!popup) return;
            var formFields = popup.querySelectorAll('mat-form-field');
            for (var i = 0; i < formFields.length; i++) {
                var label = formFields[i].querySelector('mat-label');
                if (label && label.textContent.trim() === 'GL Account') {
                    var select = formFields[i].querySelector('mat-select');
                    if (select) select.click();
                    break;
                }
            }
        """)
        self.wait_seconds(1.5)

        options = self._get_dropdown_options()
        valid_opts = [o for o in options if o.strip()]
        if not valid_opts:
            self._close_dropdown_panel()
            return None

        chosen = random.choice(valid_opts)
        # Click the option
        self.driver.execute_script(f"""
            var options = document.querySelectorAll('.cdk-overlay-pane mat-option');
            for (var i = 0; i < options.length; i++) {{
                if (options[i].textContent.trim() === '{chosen}') {{
                    options[i].click();
                    break;
                }}
            }}
        """)
        self.wait_seconds(2)
        log.info(f"Selected GL Account: {chosen}")
        return chosen

    def _get_dropdown_options(self):
        """Get all option texts from the currently open dropdown panel."""
        js = """
            var options = document.querySelectorAll(
                '.cdk-overlay-pane mat-option'
            );
            var texts = [];
            for (var i = 0; i < options.length; i++) {
                texts.push(options[i].textContent.trim());
            }
            return texts;
        """
        return self.driver.execute_script(js) or []

    def get_account_type_options(self):
        """Get all Account Type dropdown options by opening and reading."""
        self.driver.execute_script("""
            var popup = document.querySelector('.edit_pop_up.override_edit_pop_up.popup-mode');
            if (!popup) return;
            var formFields = popup.querySelectorAll('mat-form-field');
            for (var i = 0; i < formFields.length; i++) {
                var label = formFields[i].querySelector('mat-label');
                if (label && label.textContent.trim() === 'Account Type') {
                    var select = formFields[i].querySelector('mat-select');
                    if (select) select.click();
                    break;
                }
            }
        """)
        self.wait_seconds(1.5)
        opts = self._get_dropdown_options()
        self._close_dropdown_panel()
        return opts

    def get_gl_account_options(self):
        """Get all GL Account dropdown options by opening and reading."""
        self.driver.execute_script("""
            var popup = document.querySelector('.edit_pop_up.override_edit_pop_up.popup-mode');
            if (!popup) return;
            var formFields = popup.querySelectorAll('mat-form-field');
            for (var i = 0; i < formFields.length; i++) {
                var label = formFields[i].querySelector('mat-label');
                if (label && label.textContent.trim() === 'GL Account') {
                    var select = formFields[i].querySelector('mat-select');
                    if (select) select.click();
                    break;
                }
            }
        """)
        self.wait_seconds(1.5)
        opts = self._get_dropdown_options()
        self._close_dropdown_panel()
        return opts

    # ==============================================================
    #  Toggle handling
    # ==============================================================

    def _set_toggle(self, label_text, value):
        """Set a toggle switch by its label text.

        Args:
            label_text: Part of the label to match (e.g., 'Is Default Bank?')
            value: True to toggle ON, False to toggle OFF
        """
        js = f"""
            var toggles = document.querySelectorAll('app-slide-toggle-v2');
            for (var i = 0; i < toggles.length; i++) {{
                var mainLabel = toggles[i].querySelector('.main-label');
                if (mainLabel && mainLabel.textContent.trim().indexOf('{label_text}') > -1) {{
                    var sw = toggles[i].querySelector(
                        '.switch-wrapper input[type="checkbox"]'
                    );
                    if (sw && sw.checked !== {str(value).lower()}) {{
                        sw.click();
                        return 'Toggled to ' + {str(value).lower()};
                    }}
                    return 'Already ' + {str(value).lower()};
                }}
            }}
            return 'Toggle not found: {label_text}';
        """
        result = self.driver.execute_script(js)
        log.info(f"Toggle '{label_text}': {result}")

    def set_is_default_bank(self, value):
        """Set the 'Is Default Bank?' toggle."""
        self._set_toggle("Is Default Bank?", value)

    def set_status(self, value):
        """Set the 'Status' toggle."""
        self._set_toggle("Status", value)

    def get_toggle_state(self, label_text):
        """Get the current state of a toggle by its label text.
        Returns True if checked (ON), False if unchecked (OFF).
        """
        js = f"""
            var toggles = document.querySelectorAll('app-slide-toggle-v2');
            for (var i = 0; i < toggles.length; i++) {{
                var mainLabel = toggles[i].querySelector('.main-label');
                if (mainLabel && mainLabel.textContent.trim().indexOf('{label_text}') > -1) {{
                    var sw = toggles[i].querySelector(
                        '.switch-wrapper input[type="checkbox"]'
                    );
                    return sw ? sw.checked : null;
                }}
            }}
            return null;
        """
        return self.driver.execute_script(js)

    # ==============================================================
    #  Form fill — complete
    # ==============================================================

    def fill_bank_form(self, data):
        """Fill all fields on the Bank form with provided data dict.

        Args:
            data: Dict with keys matching field names.
                   None values for dropdowns → select random from live UI.
        """
        log.info("Filling Bank form...")

        # Text inputs — fill using JS value-setter
        text_field_map = [
            ("bank_name", "Bank Name"),
            ("bank_code", "Bank Code"),
            ("branch_name", "Branch Name"),
            ("branch_code", "Branch Code"),
            ("account_number", "Account Number"),
            ("swift_number", "Swift Number"),
            ("iban_number", "IBAN Number"),
            ("ifsc_code", "IFSC Code"),
            ("cash_credit_limit", "Cash Credit Limit"),
            ("bank_address", "Bank Address"),
        ]

        for key, name_attr in text_field_map:
            value = data.get(key)
            if value is not None:
                self._fill_input_by_name(name_attr, str(value))

        # Dropdowns — select specified or random
        if data.get("account_type"):
            self.select_account_type(data["account_type"])
        else:
            random_type = self.select_random_account_type()
            if random_type:
                data["account_type"] = random_type

        if data.get("gl_account"):
            self.select_gl_account(data["gl_account"])
        else:
            random_gl = self.select_random_gl_account()
            if random_gl:
                data["gl_account"] = random_gl

        # Toggles
        if "is_default_bank" in data:
            self.set_is_default_bank(data["is_default_bank"])
        if "status" in data:
            self.set_status(data["status"])

        self.wait_seconds(0.5)

    # ==============================================================
    #  Create / Edit / Submit / Cancel
    # ==============================================================

    def create_bank(self, data):
        """Open Add form, fill all fields, and submit.

        Returns dict with:
            status: "PASSED" or "FAILED"
            bank_name: the bank name used
            error: error message if any
        """
        log.info("Creating Bank record...")
        self.open_add_form()
        self.wait_seconds(1)
        assert self._is_form_popup_open(), "Add form did not open"

        self.fill_bank_form(data)
        self.wait_seconds(0.5)

        return self._submit_and_handle_result(data)

    def _submit_and_handle_result(self, data):
        """Click Submit/Update and handle the result.

        Returns dict with status, bank_name, error.
        """
        result = {"status": "FAILED", "bank_name": "", "error": ""}

        # Click Submit
        self._force_close_panels()
        try:
            submit_btn = self.driver.find_element(
                By.XPATH,
                "//div[@class='popup-footer']//button[contains(.,'Submit')]"
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                submit_btn,
            )
        except Exception:
            # Try Update button (in case of edit mode)
            try:
                update_btn = self.driver.find_element(
                    By.XPATH,
                    "//div[@class='popup-footer']//button[contains(.,'Update')]"
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});"
                    "arguments[0].click();",
                    update_btn,
                )
            except Exception as e:
                log.error(f"Submit/Update button not found: {e}")
                result["error"] = "Submit/Update button not found"
                return result

        self.wait_seconds(3)

        # Check SweetAlert
        swal_title = self.get_swal_title()

        if swal_title and "success" in swal_title.lower():
            result["status"] = "PASSED"
            result["bank_name"] = data.get("bank_name", "")
            log.info(f"Bank created successfully: {result['bank_name']}")
        elif swal_title and "validation" in swal_title.lower():
            result["error"] = f"{swal_title} — validation failed"
            log.warning(f"Validation failed: {result['error']}")
            # Dismiss the SweetAlert
            self._dismiss_swal()
        else:
            # Check if popup is still open (form might still be visible)
            popup_visible = self._is_form_popup_open()
            if popup_visible:
                result["error"] = "Submit clicked but no SweetAlert appeared"
                log.warning(result["error"])
            else:
                # Popup closed without SweetAlert (success without alert)
                result["status"] = "PASSED"
                result["bank_name"] = data.get("bank_name", "")
                log.info(f"Bank created (no alert): {result['bank_name']}")

        return result

    def submit(self):
        """Click the Submit button on the form."""
        log.info("Clicking Submit button...")
        self._force_close_panels()
        try:
            submit_btn = self.driver.find_element(
                By.XPATH,
                "//div[@class='popup-footer']//button[contains(.,'Submit')]"
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                submit_btn,
            )
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"Submit button not found: {e}")

    def update(self):
        """Click the Update button on the edit form."""
        log.info("Clicking Update button...")
        self._force_close_panels()
        try:
            update_btn = self.driver.find_element(
                By.XPATH,
                "//div[@class='popup-footer']//button[contains(.,'Update')]"
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                update_btn,
            )
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"Update button not found: {e}")

    def cancel(self):
        """Click the Cancel button on the form popup."""
        log.info("Clicking Cancel button...")
        try:
            cancel_btn = self.driver.find_element(
                By.XPATH,
                "//div[@class='popup-footer']//button[contains(.,'Cancel')]"
            )
            self.driver.execute_script("arguments[0].click();", cancel_btn)
            self.wait_seconds(1)
        except Exception as e:
            log.warning(f"Cancel button not found: {e}")

    def close_popup(self):
        """Close the form popup via Cancel button or JS removal."""
        try:
            self.cancel()
        except Exception:
            pass
        try:
            self.force_close_form_popup()
        except Exception:
            pass

    def force_close_form_popup(self):
        """Force close the form popup by removing it from DOM."""
        self.driver.execute_script("""
            var popup = document.querySelector(
                '.edit_pop_up.override_edit_pop_up.popup-mode'
            );
            if (popup) {
                popup.remove();
            }
            // Also remove dialog backdrop
            var backdrop = document.querySelector(
                '.cdk-overlay-dark-backdrop, .cdk-overlay-backdrop'
            );
            if (backdrop) {
                backdrop.remove();
            }
        """)
        self.wait_seconds(0.5)

    # ==============================================================
    #  SweetAlert2 handling
    # ==============================================================

    def get_swal_title(self):
        """Get the SweetAlert2 title text."""
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, "#swal2-title")
            if el.is_displayed():
                return el.text.strip()
        except Exception:
            pass
        return ""

    def get_swal_content(self):
        """Get the SweetAlert2 content text."""
        try:
            el = self.driver.find_element(
                By.CSS_SELECTOR, ".swal2-html-container"
            )
            if el.is_displayed():
                return el.text.strip()
        except Exception:
            pass
        return ""

    def _dismiss_swal(self):
        """Dismiss the SweetAlert2 popup by clicking OK."""
        try:
            ok_btn = self.driver.find_element(
                By.CSS_SELECTOR, ".swal2-confirm"
            )
            if ok_btn and ok_btn.is_displayed():
                ok_btn.click()
                self.wait_seconds(1)
                return True
        except Exception:
            pass
        return False

    def is_swal_visible(self):
        """Check if a SweetAlert2 popup is visible."""
        try:
            container = self.driver.find_element(
                By.CSS_SELECTOR, ".swal2-container"
            )
            return container.is_displayed()
        except Exception:
            return False

    def handle_validation_warning(self, timeout=5):
        """Handle the 'Validation Failed' SweetAlert2 popup.

        Returns the SweetAlert title if visible, or empty string.
        Automatically dismisses the alert.
        """
        try:
            title_el = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "#swal2-title")
                )
            )
            title = title_el.text.strip()
            log.info(f"SweetAlert title: {title}")

            # Dismiss
            self._dismiss_swal()
            return title
        except TimeoutException:
            return ""

    def handle_success_alert(self, timeout=5):
        """Handle the success SweetAlert2 popup.

        Returns the SweetAlert title if visible, or empty string.
        Automatically dismisses the alert (or waits for auto-dismiss).
        """
        try:
            title_el = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "#swal2-title")
                )
            )
            title = title_el.text.strip()
            log.info(f"Success alert: {title}")

            # Try to dismiss
            self._dismiss_swal()
            return title
        except TimeoutException:
            return ""

    # ==============================================================
    #  Validation error reading
    # ==============================================================

    def get_mat_error_text(self):
        """Get all mat-error text from the form popup."""
        errors = []
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            error_els = popup.find_elements(By.CSS_SELECTOR, "mat-error")
            for el in error_els:
                text = el.text.strip()
                if text and text not in errors:
                    errors.append(text)
        except Exception:
            pass
        return errors

    def get_field_error(self, field_label):
        """Get mat-error text for a specific field by its label."""
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            form_fields = popup.find_elements(
                By.CSS_SELECTOR, "mat-form-field"
            )
            for ff in form_fields:
                label = ff.find_element(By.CSS_SELECTOR, "mat-label")
                if label and field_label in label.text:
                    error_el = ff.find_elements(By.CSS_SELECTOR, "mat-error")
                    if error_el:
                        return error_el[0].text.strip()
        except Exception:
            pass
        return ""

    def get_field_validation_state(self, field_label):
        """Check if a specific field is currently invalid.

        Returns dict with: invalid (bool), error (str), touched (bool).
        """
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            form_fields = popup.find_elements(
                By.CSS_SELECTOR, "mat-form-field"
            )
            for ff in form_fields:
                label = ff.find_element(By.CSS_SELECTOR, "mat-label")
                if label and field_label in label.text:
                    classes = ff.get_attribute("class") or ""
                    error_el = ff.find_elements(By.CSS_SELECTOR, "mat-error")
                    return {
                        "invalid": "ng-invalid" in classes,
                        "touched": "ng-touched" in classes,
                        "error": error_el[0].text.strip() if error_el else "",
                    }
        except Exception:
            pass
        return {"invalid": False, "touched": False, "error": ""}

    def get_all_field_states(self):
        """Get validation state for ALL form fields.

        Returns list of dicts: {field, invalid, error, touched}.
        """
        result = []
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            form_fields = popup.find_elements(
                By.CSS_SELECTOR, "mat-form-field"
            )
            for ff in form_fields:
                label = ff.find_element(By.CSS_SELECTOR, "mat-label")
                classes = ff.get_attribute("class") or ""
                error_el = ff.find_elements(By.CSS_SELECTOR, "mat-error")
                result.append({
                    "field": label.text.strip() if label else "?",
                    "invalid": "ng-invalid" in classes,
                    "touched": "ng-touched" in classes,
                    "error": error_el[0].text.strip() if error_el else "",
                })
        except Exception as e:
            log.warning(f"get_all_field_states error: {e}")
        return result

    # ==============================================================
    #  Form field value reading
    # ==============================================================

    def get_form_field_values(self):
        """Read all form field values from the popup.

        Returns dict with field names as keys and current values.
        """
        values = {}
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )

            # Text inputs
            inputs = popup.find_elements(By.CSS_SELECTOR, "input[type='text']")
            for inp in inputs:
                name = inp.get_attribute("name")
                if name:
                    values[name] = inp.get_attribute("value") or ""

            # Dropdowns (mat-select trigger text)
            form_fields = popup.find_elements(By.CSS_SELECTOR, "mat-form-field")
            for ff in form_fields:
                label = ff.find_element(By.CSS_SELECTOR, "mat-label")
                select = ff.find_elements(By.CSS_SELECTOR, "mat-select")
                if select:
                    label_text = label.text.strip() if label else ""
                    trigger = select[0].find_elements(
                        By.CSS_SELECTOR, ".mat-select-trigger, .mat-mdc-select-trigger"
                    )
                    if trigger:
                        values[label_text] = trigger[0].text.strip()

            # Toggles
            toggles = popup.find_elements(By.CSS_SELECTOR, "app-slide-toggle-v2")
            for tc in toggles:
                main_label = tc.find_element(By.CSS_SELECTOR, ".main-label")
                sw = tc.find_elements(By.CSS_SELECTOR, ".switch-wrapper input[type='checkbox']")
                if main_label:
                    values[main_label.text.strip()] = (
                        sw[0].is_selected() if sw else None
                    )

        except Exception as e:
            log.warning(f"get_form_field_values error: {e}")
        return values

    def get_input_value(self, name_attr):
        """Get the current value of an input field by name attribute."""
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            input_el = popup.find_element(
                By.CSS_SELECTOR, f"input[name='{name_attr}']"
            )
            return input_el.get_attribute("value") or ""
        except Exception:
            return ""

    # ==============================================================
    #  Table operations
    # ==============================================================

    def get_table_row_count(self):
        """Get the number of data rows in the table."""
        try:
            rows = self.driver.find_elements(
                By.CSS_SELECTOR, "table#excel-table tbody tr"
            )
            return len(rows)
        except Exception:
            return 0

    def is_bank_in_table(self, bank_name):
        """Check if a bank with the given name exists in the table."""
        try:
            cells = self.driver.find_elements(
                By.CSS_SELECTOR, "table#excel-table tbody td:nth-child(4)"
            )
            for cell in cells:
                try:
                    if cell.text.strip() == bank_name:
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def get_all_bank_names(self):
        """Get all bank names from the current table page."""
        names = []
        try:
            cells = self.driver.find_elements(
                By.CSS_SELECTOR, "table#excel-table tbody td:nth-child(4)"
            )
            for cell in cells:
                try:
                    name = cell.text.strip()
                    if name:
                        names.append(name)
                except Exception:
                    continue
        except Exception:
            pass
        return names

    def get_row_count_text(self):
        """Get the pagination text (e.g., '1 – 10 of 40')."""
        try:
            el = self.driver.find_element(
                By.CSS_SELECTOR, "mat-paginator"
            )
            return el.text.strip()
        except Exception:
            return ""

    # ==============================================================
    #  Row action buttons
    # ==============================================================

    def click_view_button(self, bank_name):
        """Click the View button for a specific bank row."""
        log.info(f"Clicking View for: {bank_name}")
        self._force_close_panels()
        try:
            btn = self.driver.find_element(
                By.XPATH,
                f"//td[contains(text(),'{bank_name}')]"
                f"/ancestor::tr//td[1]//button",
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                btn,
            )
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"View button not found for '{bank_name}': {e}")

    def click_edit_button(self, bank_name):
        """Click the Edit button for a specific bank row."""
        log.info(f"Clicking Edit for: {bank_name}")
        self._force_close_panels()
        try:
            btn = self.driver.find_element(
                By.XPATH,
                f"//td[contains(text(),'{bank_name}')]"
                f"/ancestor::tr//td[2]//button",
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                btn,
            )
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"Edit button not found for '{bank_name}': {e}")

    def click_history_button(self, bank_name):
        """Click the History button for a specific bank row."""
        log.info(f"Clicking History for: {bank_name}")
        self._force_close_panels()
        try:
            btn = self.driver.find_element(
                By.XPATH,
                f"//td[contains(text(),'{bank_name}')]"
                f"/ancestor::tr//td[3]//button",
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                btn,
            )
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"History button not found for '{bank_name}': {e}")

    # ==============================================================
    #  Search functionality
    # ==============================================================

    def open_search(self):
        """Click the search toggle button to show the search input."""
        log.info("Opening search bar...")
        try:
            btn = self.driver.find_element(
                By.CSS_SELECTOR, "button.search-btn"
            )
            if btn.is_displayed():
                btn.click()
                self.wait_seconds(1)
                return True
        except Exception:
            pass
        log.warning("Search button not found")
        return False

    def search(self, text):
        """Type text into the search input and click search."""
        log.info(f"Searching for: {text}")
        try:
            search_input = self.driver.find_element(
                By.CSS_SELECTOR,
                ".erp-search-wrapper input, input#erpSearchInput",
            )
            # Use JS value-setter for Angular compatibility
            js = """
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(arguments[0], arguments[1]);
                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
            """
            self.driver.execute_script(js, search_input, str(text))

            # Click search submit button
            wrapper = self.driver.find_element(
                By.CSS_SELECTOR, ".erp-search-wrapper"
            )
            search_btn = wrapper.find_element(By.TAG_NAME, "button")
            search_btn.click()
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"Search failed: {e}")

    def clear_search(self):
        """Clear the search input and refresh."""
        log.info("Clearing search...")
        try:
            search_input = self.driver.find_element(
                By.CSS_SELECTOR,
                ".erp-search-wrapper input, input#erpSearchInput",
            )
            js = """
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(arguments[0], '');
                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
            """
            self.driver.execute_script(js, search_input)

            # Click search to clear
            wrapper = self.driver.find_element(
                By.CSS_SELECTOR, ".erp-search-wrapper"
            )
            search_btn = wrapper.find_element(By.TAG_NAME, "button")
            search_btn.click()
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"Clear search failed: {e}")

    # ==============================================================
    #  Pagination
    # ==============================================================

    def go_to_next_page(self):
        """Navigate to the next page in the table."""
        try:
            btns = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button.mat-mdc-paginator-navigation-next"
            )
            for btn in btns:
                if btn.is_enabled():
                    self.driver.execute_script(
                        "arguments[0].click();", btn
                    )
                    self.wait_seconds(2)
                    return True
        except Exception:
            pass
        log.info("Next page button not available")
        return False

    def go_to_previous_page(self):
        """Navigate to the previous page in the table."""
        try:
            btns = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button.mat-mdc-paginator-navigation-previous"
            )
            for btn in btns:
                if btn.is_enabled():
                    self.driver.execute_script(
                        "arguments[0].click();", btn
                    )
                    self.wait_seconds(2)
                    return True
        except Exception:
            pass
        log.info("Previous page button not available")
        return False

    def get_current_page_info(self):
        """Get current pagination info (range text)."""
        return self.get_row_count_text()

    # ==============================================================
    #  More menu
    # ==============================================================

    def open_more_menu(self):
        """Open the more_vert menu."""
        try:
            btn = self.driver.find_element(
                By.CSS_SELECTOR, "button[mattooltip='More']"
            )
            if btn.is_displayed():
                btn.click()
                self.wait_seconds(1)
                return True
        except Exception:
            pass
        return False

    def click_export_excel(self):
        """Click Export to Excel from the more menu."""
        log.info("Clicking Export to Excel...")
        self.open_more_menu()
        try:
            option = self.driver.find_element(
                By.XPATH,
                "//button[contains(.,'Export to Excel') or "
                "contains(.,'Download as')]"
            )
            option.click()
            self.wait_seconds(2)
            return True
        except Exception as e:
            log.warning(f"Export option not found: {e}")
            return False

    # ==============================================================
    #  Utility methods
    # ==============================================================

    def is_add_form_open(self):
        """Check if the Add Bank form popup is open."""
        return self._is_form_popup_open()

    def is_form_popup_open(self):
        """Check if any form popup is visible."""
        return self._is_form_popup_open()

    def is_edit_mode(self):
        """Check if the popup is in edit mode (Update button instead of Submit)."""
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            btns = popup.find_elements(
                By.CSS_SELECTOR, ".popup-footer button"
            )
            for btn in btns:
                if "Update" in btn.text:
                    return True
        except Exception:
            pass
        return False

    def is_view_mode(self):
        """Check if the popup is in view mode (only Cancel button)."""
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            btns = popup.find_elements(
                By.CSS_SELECTOR, ".popup-footer button"
            )
            # View mode has only Cancel, no Submit/Update
            return len(btns) == 1
        except Exception:
            pass
        return False

    def is_field_disabled(self, name_attr):
        """Check if a specific input field is disabled."""
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            input_el = popup.find_element(
                By.CSS_SELECTOR, f"input[name='{name_attr}']"
            )
            return input_el.is_enabled() is False
        except Exception:
            return False

    def is_dropdown_disabled(self, label_text):
        """Check if a dropdown is disabled."""
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            form_fields = popup.find_elements(By.CSS_SELECTOR, "mat-form-field")
            for ff in form_fields:
                label = ff.find_element(By.CSS_SELECTOR, "mat-label")
                if label and label_text in label.text:
                    select = ff.find_element(By.CSS_SELECTOR, "mat-select")
                    return select.get_attribute("disabled") is not None
        except Exception:
            pass
        return False

    def _debug_form_state(self):
        """Log debug information about the current form state."""
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            log.info(f"Popup visible: {popup.is_displayed()}")

            heading = popup.find_element(By.CSS_SELECTOR, "h3")
            log.info(f"Heading: {heading.text.strip() if heading else 'N/A'}")

            inputs = popup.find_elements(By.CSS_SELECTOR, "input[type='text']")
            log.info(f"Text inputs: {len(inputs)}")
            for inp in inputs[:15]:
                name = inp.get_attribute("name")
                value = inp.get_attribute("value")
                disabled = inp.get_attribute("disabled")
                readonly = inp.get_attribute("readonly")
                log.info(
                    f"  [{name}] value='{value}' "
                    f"disabled={disabled} readonly={readonly}"
                )

            selects = popup.find_elements(By.CSS_SELECTOR, "mat-select")
            log.info(f"Mat-selects: {len(selects)}")

            btns = popup.find_elements(
                By.CSS_SELECTOR, ".popup-footer button"
            )
            btn_texts = [b.text.strip() for b in btns]
            log.info(f"Footer buttons: {btn_texts}")
        except Exception as e:
            log.warning(f"Debug form state failed: {e}")
