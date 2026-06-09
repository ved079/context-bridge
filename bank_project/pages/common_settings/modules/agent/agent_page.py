"""
agent_page.py
-------------
Page Object Model for RhythmERP Agent screen.

Location: Common Settings > Agent
URL:      /#/dynamic-screens/Agent

FORM LAYOUT (3-step STEPPER form):

  STEP 1 — Universal Fields + Address Details:
    Party Reference, Agent Name*, Phone Number*, Email, Status
    Address Details table (add row): Country*, State*, District*, Taluka*,
    Village, Address*, Pin Code*

  STEP 2 — Payment Details:
    Payment Terms, Preferred Payment Method, Is GST Set Off

  STEP 3 — Bank Details:
    Bank Details table (add row): Bank Name*, Branch, IFSC Code,
    Account Type*, Account Holder Name*, Account Number*,
    Bank Proof*, Attachment

KEY DIFFERENCES FROM BANK SCREEN:
  - STEPPER FORM (3 steps with Next/Previous navigation)
  - Table rows WITHIN the form (Address + Bank — add row buttons)
  - Cascading dropdowns (Country→State→District→Taluka→Village)
  - Multiple bank rows possible

CRITICAL LESSONS (from Bank screen BUG-004):
  - Angular Material inputs: get_attribute('value') returns null
  - MUST use execute_script with inp.value for reading input values
  - mat-select clicks may not sync Angular form model — use JS workaround
  - NEVER use Keys.ESCAPE to close overlay panels
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


class AgentPage(BasePage):
    PAGE_URL = f"{RHYTHMERP_BASE_URL}/#/dynamic-screens/Agent"

    # ==============================================================
    #  LOCATORS — Toolbar
    # ==============================================================
    ADD_BUTTON = ("css", "button.erp-add-btn")
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
    TABLE_AGENT_NAME_CELLS = ("css", "table#excel-table tbody td:nth-child(4)")
    TABLE_PHONE_CELLS = ("css", "table#excel-table tbody td:nth-child(5)")
    TABLE_STATUS_CELLS = ("css", "table#excel-table tbody td:nth-child(6)")
    NO_DATA_ROW = (
        "css",
        "table#excel-table tbody tr td.no-data, "
        "table#excel-table tbody tr.mat-mdc-no-data-row",
    )

    # ==============================================================
    #  LOCATORS — Form popup
    # ==============================================================
    FORM_POPUP = ("css", ".edit_pop_up.override_edit_pop_up.popup-mode")
    FORM_HEADING = (
        "css",
        ".edit_pop_up h3, .edit_pop_up.override_edit_pop_up.popup-mode h3",
    )

    # ==============================================================
    #  LOCATORS — Stepper
    # ==============================================================
    STEPPER_TABS = ("css", "[role='tab']")
    STEPPER_NEXT = ("css", "button.mat-stepper-next")
    STEPPER_PREV = ("css", "button.mat-stepper-previous")

    # ==============================================================
    #  LOCATORS — Universal text inputs (by name attribute)
    # ==============================================================
    AGENT_NAME_INPUT = ("css", "input[name='Agent Name']")
    PHONE_NUMBER_INPUT = ("css", "input[name='Phone Number']")
    EMAIL_INPUT = ("css", "input[name='Email']")

    # ==============================================================
    #  LOCATORS — Address text inputs (by name attribute)
    # ==============================================================
    ADDRESS_INPUT = ("css", "input[name='Address']")
    PIN_CODE_INPUT = ("css", "input[name='Pin Code']")

    # ==============================================================
    #  LOCATORS — Bank text inputs (by name attribute)
    # ==============================================================
    BANK_NAME_INPUT = ("css", "input[name='Bank Name']")
    BRANCH_INPUT = ("css", "input[name='Branch']")
    IFSC_CODE_INPUT = ("css", "input[name='IFSC Code']")
    ACCOUNT_HOLDER_NAME_INPUT = ("css", "input[name='Account Holder Name']")
    ACCOUNT_NUMBER_INPUT = ("css", "input[name='Account Number']")

    # ==============================================================
    #  LOCATORS — Dropdowns (mat-select, by mat-label XPath)
    # ==============================================================
    PARTY_REFERENCE_SELECT = (
        "xpath",
        "//mat-label[contains(.,'Party Reference')]"
        "/ancestor::mat-form-field//mat-select",
    )
    COUNTRY_SELECT = (
        "xpath",
        "//mat-label[contains(.,'Country')]"
        "/ancestor::mat-form-field//mat-select",
    )
    STATE_SELECT = (
        "xpath",
        "//mat-label[contains(.,'State')]"
        "/ancestor::mat-form-field//mat-select",
    )
    DISTRICT_SELECT = (
        "xpath",
        "//mat-label[contains(.,'District')]"
        "/ancestor::mat-form-field//mat-select",
    )
    TALUKA_SELECT = (
        "xpath",
        "//mat-label[contains(.,'Taluka')]"
        "/ancestor::mat-form-field//mat-select",
    )
    VILLAGE_SELECT = (
        "xpath",
        "//mat-label[contains(.,'Village')]"
        "/ancestor::mat-form-field//mat-select",
    )
    PAYMENT_TERMS_SELECT = (
        "xpath",
        "//mat-label[contains(.,'Payment Terms')]"
        "/ancestor::mat-form-field//mat-select",
    )
    PREFERRED_PAYMENT_METHOD_SELECT = (
        "xpath",
        "//mat-label[contains(.,'Preferred Payment Method')]"
        "/ancestor::mat-form-field//mat-select",
    )
    ACCOUNT_TYPE_SELECT = (
        "xpath",
        "//mat-label[contains(.,'Account Type')]"
        "/ancestor::mat-form-field//mat-select",
    )
    BANK_PROOF_SELECT = (
        "xpath",
        "//mat-label[contains(.,'Bank Proof')]"
        "/ancestor::mat-form-field//mat-select",
    )

    # ==============================================================
    #  LOCATORS — Toggles (app-slide-toggle-v2)
    # ==============================================================
    STATUS_TOGGLE = (
        "xpath",
        "//app-slide-toggle-v2[.//span[contains(@class,'main-label') "
        "and contains(.,'Status')]]"
        "//div[contains(@class,'switch-wrapper')]",
    )
    GST_SET_OFF_TOGGLE = (
        "xpath",
        "//app-slide-toggle-v2[.//span[contains(@class,'main-label') "
        "and contains(.,'Is GST Set Off')]]"
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
    #  LOCATORS — Row action buttons (parametrised by agent name)
    # ==============================================================
    VIEW_BUTTON = (
        "xpath",
        "//td[contains(text(),'{agent_name}')]"
        "/ancestor::tr//td[1]//button",
    )
    EDIT_BUTTON = (
        "xpath",
        "//td[contains(text(),'{agent_name}')]"
        "/ancestor::tr//td[2]//button",
    )
    HISTORY_BUTTON = (
        "xpath",
        "//td[contains(text(),'{agent_name}')]"
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

    # ==============================================================
    #  LOCATORS — Pagination
    # ==============================================================
    PAGINATION_NEXT = (
        "css",
        "button[aria-label='Next page'], button.mat-mdc-paginator-navigation-next",
    )
    PAGINATION_PREV = (
        "css",
        "button[aria-label='Previous page'], "
        "button.mat-mdc-paginator-navigation-previous",
    )
    ITEMS_PER_PAGE_SELECT = (
        "css",
        "mat-paginator-page-size select, .mat-mdc-paginator-page-size select",
    )

    # ==============================================================
    #  Navigation & page load
    # ==============================================================

    def navigate_to_page(self):
        """Navigate to the Agent listing page."""
        log.info("Navigating to Agent page...")
        self.navigate_to(self.PAGE_URL)
        self.driver.refresh()
        self._wait_for_page_ready()

    def _wait_for_page_ready(self):
        """Wait until the Agent page is fully loaded."""
        try:
            WebDriverWait(self.driver, EXPLICIT_WAIT).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "table#excel-table")
                )
            )
            log.info("Agent table loaded")
        except TimeoutException:
            log.warning("Agent table not found, page may be empty")

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ul.tbl-export-btn")
                )
            )
            self.wait_seconds(1)
            log.info("Agent toolbar ready")
        except TimeoutException:
            log.warning("Toolbar not found, ADD button may be delayed")
            self.wait_seconds(3)

    def is_page_loaded(self):
        """Check if the Agent listing page has loaded."""
        return self.is_displayed(self.TABLE, timeout=10)

    # ==============================================================
    #  Overlay cleanup — NEVER use Keys.ESCAPE
    # ==============================================================

    def _force_close_panels(self):
        """Remove ALL select overlay panes from the DOM via JS."""
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

    def _close_dropdown_panel(self):
        """Close any open dropdown overlay panel."""
        self._close_select_panel()

    # ==============================================================
    #  Toolbar actions
    # ==============================================================

    def open_add_form(self):
        """Click the ADD button to open the Agent create form (stepper)."""
        log.info("Clicking ADD Agent button...")
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

        # Strategy 2: mini-fab with 'add' icon
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

        # Strategy 3: Button with 'Add Agent' text
        try:
            btns = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in btns:
                try:
                    if "Add Agent" in btn.text and btn.is_displayed():
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

        raise Exception("ADD Agent button not found or not clickable")

    def _wait_for_toolbar(self):
        """Wait for the toolbar and ADD button to be present."""
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
                        if "Add Agent" in btn.text and btn.is_displayed():
                            return
                    except Exception:
                        continue
            except Exception:
                pass
            log.info(f"Waiting for toolbar... attempt {attempt + 1}/3")
            self.wait_seconds(2)
        log.warning("Toolbar wait exhausted")

    def _is_form_popup_open(self):
        """Quick check if the Agent form popup is visible."""
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
        """Click the Refresh button. Falls back to page navigate."""
        log.info("Clicking Refresh button...")
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
        log.warning("Refresh button not found, using page re-navigate")
        self.navigate_to(self.PAGE_URL)
        self._wait_for_page_ready()

    # ==============================================================
    #  Form filling — JS value-setter for Angular compatibility
    # ==============================================================

    def _fill_input_by_name(self, name_attr, value):
        """Fill an input field by its name attribute using JS value-setter."""
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

    def _clear_input_by_name(self, name_attr):
        """Clear an input field by its name attribute."""
        self._fill_input_by_name(name_attr, "")

    # ==============================================================
    #  Dropdown selection — JS approach (AGT-BUG-001)
    # ==============================================================

    def _select_mat_option_by_label_and_value(self, label_text, option_text):
        """Select a mat-select dropdown option using JS.

        Workaround for AGT-BUG-001: browser-clicked mat-options don't
        reliably update Angular reactive form model.
        """
        js = f"""
            var popup = document.querySelector(
                '.edit_pop_up.override_edit_pop_up.popup-mode'
            );
            if (!popup) return 'No popup';
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
            targetSelect.click();
        """
        result1 = self.driver.execute_script(js)
        self.wait_seconds(2)

        js2 = f"""
            var options = document.querySelectorAll('.cdk-overlay-pane mat-option');
            for (var i = 0; i < options.length; i++) {{
                if (options[i].textContent.trim() === '{option_text}') {{
                    options[i].click();
                    return 'Selected: {option_text}';
                }}
            }}
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

    def _select_cascading_dropdown(self, label_text, option_text):
        """Select a cascading dropdown with extra wait for options to load."""
        result = self._select_mat_option_by_label_and_value(label_text, option_text)
        # Cascading dropdowns need extra time for child options to load
        self.wait_seconds(3)
        return result

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

    def _select_random_option(self, label_text):
        """Open a dropdown by label, select a random valid option.
        Returns the selected option text or None.
        """
        log.info(f"Selecting random option for: {label_text}")
        js = f"""
            var popup = document.querySelector('.edit_pop_up.override_edit_pop_up.popup-mode');
            if (!popup) return;
            var formFields = popup.querySelectorAll('mat-form-field');
            for (var i = 0; i < formFields.length; i++) {{
                var label = formFields[i].querySelector('mat-label');
                if (label && label.textContent.trim() === '{label_text}') {{
                    var select = formFields[i].querySelector('mat-select');
                    if (select) select.click();
                    break;
                }}
            }}
        """
        self.driver.execute_script(js)
        self.wait_seconds(1.5)

        options = self._get_dropdown_options()
        valid_opts = [o for o in options if o.strip()]
        if not valid_opts:
            self._close_dropdown_panel()
            return None

        chosen = random.choice(valid_opts)
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
        log.info(f"Selected '{chosen}' for '{label_text}'")
        return chosen

    # ==============================================================
    #  Toggle handling
    # ==============================================================

    def _set_toggle(self, label_text, value):
        """Set a toggle switch by its label text."""
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

    def get_toggle_state(self, label_text):
        """Get the current state of a toggle by its label text."""
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
    #  Stepper navigation
    # ==============================================================

    def click_stepper_next(self):
        """Click the Next button to advance to the next stepper step."""
        log.info("Clicking Stepper Next button...")
        self._force_close_panels()
        try:
            btn = self.driver.find_element(
                By.CSS_SELECTOR, "button.mat-stepper-next"
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                btn,
            )
            self.wait_seconds(2)
            log.info("Stepper Next clicked")
            return True
        except Exception as e:
            log.warning(f"Stepper Next button not found: {e}")
            return False

    def click_stepper_previous(self):
        """Click the Previous button to go back one stepper step."""
        log.info("Clicking Stepper Previous button...")
        self._force_close_panels()
        try:
            btn = self.driver.find_element(
                By.CSS_SELECTOR, "button.mat-stepper-previous"
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                btn,
            )
            self.wait_seconds(2)
            log.info("Stepper Previous clicked")
            return True
        except Exception as e:
            log.warning(f"Stepper Previous button not found: {e}")
            return False

    def get_current_stepper_step(self):
        """Get the currently active stepper step (1, 2, or 3).
        Returns 0 if no step is active.
        """
        try:
            tabs = self.driver.find_elements(By.CSS_SELECTOR, "[role='tab']")
            for i, tab in enumerate(tabs):
                classes = tab.get_attribute("class") or ""
                aria_selected = tab.get_attribute("aria-selected")
                if "mat-tab-label-active" in classes or aria_selected == "true":
                    return i + 1
        except Exception:
            pass
        return 0

    # ==============================================================
    #  Add Row buttons (Address Details + Bank Details)
    # ==============================================================

    def click_add_address_row(self):
        """Click the 'add' button to add a new Address Details row."""
        log.info("Clicking Add Address Row button...")
        try:
            # Find add buttons inside the popup — look for the one near Address section
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            # Strategy: find mat-icon-button with 'add' icon
            add_btns = popup.find_elements(
                By.CSS_SELECTOR, "button.mat-mdc-icon-button"
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
                        self.wait_seconds(1)
                        log.info("Address row added")
                        return True
                except Exception:
                    continue
        except Exception as e:
            log.warning(f"Add address row failed: {e}")
        return False

    def click_add_bank_row(self):
        """Click the 'add' button to add a new Bank Details row."""
        log.info("Clicking Add Bank Row button...")
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            add_btns = popup.find_elements(
                By.CSS_SELECTOR, "button.mat-mdc-icon-button"
            )
            # Find the last 'add' button (bank section add button)
            for btn in reversed(add_btns):
                try:
                    icon = btn.find_element(By.CSS_SELECTOR, "mat-icon")
                    if icon.text.strip().lower() == "add" and btn.is_displayed():
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});"
                            "arguments[0].click();",
                            btn,
                        )
                        self.wait_seconds(1)
                        log.info("Bank row added")
                        return True
                except Exception:
                    continue
        except Exception as e:
            log.warning(f"Add bank row failed: {e}")
        return False

    def _scroll_popup_to_bottom(self):
        """Scroll the popup content area to the bottom."""
        js = """
            var popup = document.querySelector(
                '.edit_pop_up.override_edit_pop_up.popup-mode'
            );
            if (popup) {
                var scrollable = popup.querySelector('.popup-body, .popup-content, .edit_pop_up_body');
                if (scrollable) {
                    scrollable.scrollTop = scrollable.scrollHeight;
                } else {
                    popup.scrollTop = popup.scrollHeight;
                }
            }
        """
        self.driver.execute_script(js)
        self.wait_seconds(0.5)

    def _scroll_popup_to_element(self, label_text):
        """Scroll within the popup until a specific mat-label is visible."""
        js = f"""
            var popup = document.querySelector(
                '.edit_pop_up.override_edit_pop_up.popup-mode'
            );
            if (!popup) return;
            var labels = popup.querySelectorAll('mat-label');
            for (var i = 0; i < labels.length; i++) {{
                if (labels[i].textContent.trim().indexOf('{label_text}') > -1) {{
                    labels[i].scrollIntoView({{block: 'center'}});
                    return;
                }}
            }}
        """
        self.driver.execute_script(js)
        self.wait_seconds(0.5)

    # ==============================================================
    #  Form fill — complete Agent form (all 3 steps)
    # ==============================================================

    def fill_agent_form(self, data):
        """Fill all 3 steps of the Agent form with provided data dict.

        Args:
            data: Dict with keys matching field names.
                   None values for dropdowns -> select random from live UI.
        """
        log.info("Filling Agent form (Step 1: Universal + Address)...")

        # === STEP 1: Universal Fields ===
        self._fill_input_by_name("Agent Name", data.get("agent_name", ""))
        self._fill_input_by_name("Phone Number", data.get("phone_number", ""))

        if data.get("email"):
            self._fill_input_by_name("Email", data["email"])

        if "status" in data:
            self._set_toggle("Status", data["status"])

        # === STEP 1: Address Details ===
        log.info("Filling Address Details...")

        # Add an address row first
        self.click_add_address_row()
        self.wait_seconds(1)

        # Scroll down to see address fields
        self._scroll_popup_to_element("Country")

        # Cascading dropdowns: Country -> State -> District -> Taluka -> Village
        if data.get("country"):
            self._select_cascading_dropdown("Country", data["country"])
        else:
            chosen = self._select_random_option("Country")
            if chosen:
                data["country"] = chosen

        if data.get("state"):
            self._select_cascading_dropdown("State", data["state"])
        else:
            chosen = self._select_random_option("State")
            if chosen:
                data["state"] = chosen

        if data.get("district"):
            self._select_cascading_dropdown("District", data["district"])
        else:
            chosen = self._select_random_option("District")
            if chosen:
                data["district"] = chosen

        if data.get("taluka"):
            self._select_cascading_dropdown("Taluka", data["taluka"])
        else:
            chosen = self._select_random_option("Taluka")
            if chosen:
                data["taluka"] = chosen

        if data.get("village"):
            self._select_cascading_dropdown("Village", data["village"])
        # Village is optional, skip if None

        # Address and Pin Code
        if data.get("address"):
            self._fill_input_by_name("Address", data["address"])
        if data.get("pin_code"):
            self._fill_input_by_name("Pin Code", data["pin_code"])

        # === Navigate to Step 2: Payment Details ===
        log.info("Navigating to Step 2: Payment Details...")
        self._scroll_popup_to_bottom()
        self.click_stepper_next()
        self.wait_seconds(2)

        # === STEP 2: Payment Details ===
        log.info("Filling Payment Details...")

        if data.get("payment_terms"):
            self._select_mat_option_by_label_and_value(
                "Payment Terms", data["payment_terms"]
            )
        else:
            chosen = self._select_random_option("Payment Terms")
            if chosen:
                data["payment_terms"] = chosen

        if data.get("preferred_payment_method"):
            self._select_mat_option_by_label_and_value(
                "Preferred Payment Method", data["preferred_payment_method"]
            )
        else:
            chosen = self._select_random_option("Preferred Payment Method")
            if chosen:
                data["preferred_payment_method"] = chosen

        if "is_gst_set_off" in data:
            self._set_toggle("Is GST Set Off", data["is_gst_set_off"])

        # === Navigate to Step 3: Bank Details ===
        log.info("Navigating to Step 3: Bank Details...")
        self.click_stepper_next()
        self.wait_seconds(2)

        # === STEP 3: Bank Details ===
        log.info("Filling Bank Details...")

        # Add a bank row first
        self.click_add_bank_row()
        self.wait_seconds(1)

        if data.get("bank_name"):
            self._fill_input_by_name("Bank Name", data["bank_name"])
        if data.get("branch"):
            self._fill_input_by_name("Branch", data["branch"])
        if data.get("ifsc_code"):
            self._fill_input_by_name("IFSC Code", data["ifsc_code"])

        if data.get("account_type"):
            self._select_mat_option_by_label_and_value(
                "Account Type", data["account_type"]
            )
        else:
            chosen = self._select_random_option("Account Type")
            if chosen:
                data["account_type"] = chosen

        if data.get("account_holder_name"):
            self._fill_input_by_name(
                "Account Holder Name", data["account_holder_name"]
            )
        if data.get("account_number"):
            self._fill_input_by_name("Account Number", data["account_number"])

        if data.get("bank_proof"):
            self._select_mat_option_by_label_and_value(
                "Bank Proof", data["bank_proof"]
            )
        else:
            chosen = self._select_random_option("Bank Proof")
            if chosen:
                data["bank_proof"] = chosen

        self.wait_seconds(0.5)

    # ==============================================================
    #  Create / Edit / Submit / Cancel
    # ==============================================================

    def create_agent(self, data):
        """Open Add form, fill all 3 steps, and submit.

        Returns dict with:
            status: "PASSED" or "FAILED"
            agent_name: the agent name used
            error: error message if any
        """
        log.info("Creating Agent record...")
        self.open_add_form()
        self.wait_seconds(1)
        assert self._is_form_popup_open(), "Add form did not open"

        self.fill_agent_form(data)
        self.wait_seconds(0.5)

        return self._submit_and_handle_result(data)

    def _submit_and_handle_result(self, data):
        """Click Submit and handle the result."""
        result = {"status": "FAILED", "agent_name": "", "error": ""}

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

        swal_title = self.get_swal_title()
        if swal_title and "success" in swal_title.lower():
            result["status"] = "PASSED"
            result["agent_name"] = data.get("agent_name", "")
            log.info(f"Agent created successfully: {result['agent_name']}")
        elif swal_title and "validation" in swal_title.lower():
            result["error"] = f"{swal_title} — validation failed"
            log.warning(f"Validation failed: {result['error']}")
            self._dismiss_swal()
        else:
            popup_visible = self._is_form_popup_open()
            if popup_visible:
                result["error"] = "Submit clicked but no SweetAlert appeared"
                log.warning(result["error"])
            else:
                result["status"] = "PASSED"
                result["agent_name"] = data.get("agent_name", "")
                log.info(f"Agent created (no alert): {result['agent_name']}")

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
        """Close the form popup via Cancel or JS removal."""
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
            if (popup) popup.remove();
            var backdrop = document.querySelector(
                '.cdk-overlay-dark-backdrop, .cdk-overlay-backdrop'
            );
            if (backdrop) backdrop.remove();
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
        """Handle the 'Validation Failed' SweetAlert2 popup."""
        try:
            title_el = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "#swal2-title")
                )
            )
            title = title_el.text.strip()
            log.info(f"SweetAlert title: {title}")
            self._dismiss_swal()
            return title
        except TimeoutException:
            return ""

    def handle_success_alert(self, timeout=5):
        """Handle the success SweetAlert2 popup."""
        try:
            title_el = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "#swal2-title")
                )
            )
            title = title_el.text.strip()
            log.info(f"Success alert: {title}")
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

    def get_field_validation_state(self, field_label):
        """Check if a specific field is currently invalid."""
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

    # ==============================================================
    #  Form field value reading (CRITICAL: use execute_script)
    # ==============================================================

    def get_form_field_values(self):
        """Read all form field values from the popup.

        CRITICAL (AGT-BUG-004): Uses execute_script to read .value
        from Angular Material inputs, because get_attribute('value')
        returns null.
        """
        values = {}
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )

            # Text inputs — use JS to reliably read Angular Material values
            js = """
                var popup = document.querySelector(
                    '.edit_pop_up.override_edit_pop_up.popup-mode'
                );
                if (!popup) return {};
                var result = {};
                var inputs = popup.querySelectorAll('input');
                for (var i = 0; i < inputs.length; i++) {
                    var inp = inputs[i];
                    var name = inp.getAttribute('name');
                    if (name && inp.type !== 'file') {
                        result[name] = inp.value || '';
                    }
                }
                return result;
            """
            input_values = self.driver.execute_script(js)
            if input_values:
                values.update(input_values)

            # Dropdowns (mat-select trigger text)
            form_fields = popup.find_elements(By.CSS_SELECTOR, "mat-form-field")
            for ff in form_fields:
                label = ff.find_elements(By.CSS_SELECTOR, "mat-label")
                if not label:
                    continue
                select = ff.find_elements(By.CSS_SELECTOR, "mat-select")
                if select:
                    label_text = label[0].text.strip()
                    trigger = select[0].find_elements(
                        By.CSS_SELECTOR,
                        ".mat-select-trigger, .mat-mdc-select-trigger",
                    )
                    if trigger:
                        values[label_text] = trigger[0].text.strip()

            # Toggles
            toggles = popup.find_elements(By.CSS_SELECTOR, "app-slide-toggle-v2")
            for tc in toggles:
                main_label = tc.find_elements(By.CSS_SELECTOR, ".main-label")
                sw = tc.find_elements(
                    By.CSS_SELECTOR, ".switch-wrapper input[type='checkbox']"
                )
                if main_label:
                    values[main_label[0].text.strip()] = (
                        sw[0].is_selected() if sw else None
                    )

        except Exception as e:
            log.warning(f"get_form_field_values error: {e}")
        return values

    def get_input_value(self, name_attr):
        """Get the current value of an input field by name attribute.

        CRITICAL (AGT-BUG-004): Uses execute_script to read .value
        because get_attribute('value') returns null for Angular inputs.
        """
        try:
            popup = self.driver.find_element(
                By.CSS_SELECTOR,
                ".edit_pop_up.override_edit_pop_up.popup-mode",
            )
            input_el = popup.find_element(
                By.CSS_SELECTOR, f"input[name='{name_attr}']"
            )
            # Use execute_script to read .value (DOM property, not HTML attribute)
            return self.driver.execute_script(
                "return arguments[0].value", input_el
            ) or ""
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

    def is_agent_in_table(self, agent_name):
        """Check if an agent with the given name exists in the table."""
        try:
            cells = self.driver.find_elements(
                By.CSS_SELECTOR, "table#excel-table tbody td:nth-child(4)"
            )
            for cell in cells:
                try:
                    if agent_name in cell.text.strip():
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def get_all_agent_names(self):
        """Get all agent names from the current table page."""
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

    # ==============================================================
    #  Row action buttons
    # ==============================================================

    def click_view_button(self, agent_name):
        """Click the View button for a specific agent row."""
        log.info(f"Clicking View for: {agent_name}")
        self._force_close_panels()
        try:
            btn = self.driver.find_element(
                By.XPATH,
                f"//td[contains(text(),'{agent_name}')]"
                f"/ancestor::tr//td[1]//button",
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                btn,
            )
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"View button not found for '{agent_name}': {e}")

    def click_edit_button(self, agent_name):
        """Click the Edit button for a specific agent row."""
        log.info(f"Clicking Edit for: {agent_name}")
        self._force_close_panels()
        try:
            btn = self.driver.find_element(
                By.XPATH,
                f"//td[contains(text(),'{agent_name}')]"
                f"/ancestor::tr//td[2]//button",
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                btn,
            )
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"Edit button not found for '{agent_name}': {e}")

    def click_history_button(self, agent_name):
        """Click the History button for a specific agent row."""
        log.info(f"Clicking History for: {agent_name}")
        self._force_close_panels()
        try:
            btn = self.driver.find_element(
                By.XPATH,
                f"//td[contains(text(),'{agent_name}')]"
                f"/ancestor::tr//td[3]//button",
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});"
                "arguments[0].click();",
                btn,
            )
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"History button not found for '{agent_name}': {e}")

    # ==============================================================
    #  Search functionality
    # ==============================================================

    def search(self, text):
        """Type text into search input and click search."""
        log.info(f"Searching for: {text}")
        try:
            search_input = self.driver.find_element(
                By.CSS_SELECTOR,
                ".erp-search-wrapper input, input#erpSearchInput",
            )
            js = """
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(arguments[0], arguments[1]);
                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
            """
            self.driver.execute_script(js, search_input, str(text))

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

            wrapper = self.driver.find_element(
                By.CSS_SELECTOR, ".erp-search-wrapper"
            )
            search_btn = wrapper.find_element(By.TAG_NAME, "button")
            search_btn.click()
            self.wait_seconds(2)
        except Exception as e:
            log.error(f"Clear search failed: {e}")

    # ==============================================================
    #  Utility methods
    # ==============================================================

    def is_add_form_open(self):
        """Check if the Add Agent form popup is open."""
        return self._is_form_popup_open()

    def is_form_popup_open(self):
        """Check if any form popup is visible."""
        return self._is_form_popup_open()

    def is_edit_mode(self):
        """Check if the popup is in edit mode (Update button present)."""
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

    def go_to_next_page(self):
        """Navigate to the next page in the table."""
        try:
            btns = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button.mat-mdc-paginator-navigation-next",
            )
            for btn in btns:
                if btn.is_enabled():
                    self.driver.execute_script("arguments[0].click();", btn)
                    self.wait_seconds(2)
                    return True
        except Exception:
            pass
        return False

    def go_to_previous_page(self):
        """Navigate to the previous page in the table."""
        try:
            btns = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button.mat-mdc-paginator-navigation-previous",
            )
            for btn in btns:
                if btn.is_enabled():
                    self.driver.execute_script("arguments[0].click();", btn)
                    self.wait_seconds(2)
                    return True
        except Exception:
            pass
        return False
