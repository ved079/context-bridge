"""
base_page.py
------------
Base class for all Page Objects.
Contains common Selenium methods used across all pages.
Every page class (LoginPage, DashboardPage, etc.) inherits from this.
"""

import os
import time
from datetime import datetime

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    InvalidElementStateException
)

from config import EXPLICIT_WAIT, SCREENSHOT_DIR
from common.logger import log


class BasePage:
    """
    BasePage — Parent class for all Page Objects.

    Provides reusable Selenium methods:
    - Finding elements (wait-based)
    - Clicking, typing, clearing
    - Checking visibility, text, attributes
    - Screenshot capture
    - Page navigation
    """

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, EXPLICIT_WAIT)
        self.actions = ActionChains(driver)

    # ================================================================
    # ELEMENT FINDING (with explicit wait)
    # ================================================================

    def find_element(self, locator):
        """
        Find a single element using explicit wait.
        Supports tuples: ("css", "selector") or ("xpath", "//path")
        """
        by, value = self._parse_locator(locator)
        try:
            element = self.wait.until(EC.presence_of_element_located((by, value)))
            return element
        except TimeoutException:
            log.error(f"Element NOT found: {by} = '{value}'")
            raise

    def find_clickable_element(self, locator, timeout=None):
        """Find an element that is also clickable."""
        by, value = self._parse_locator(locator)
        wait_time = timeout or EXPLICIT_WAIT
        try:
            element = WebDriverWait(self.driver, wait_time).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            log.error(f"Clickable element NOT found: {by} = '{value}'")
            raise

    def find_visible_element(self, locator, timeout=None):
        """Find an element that is visible on the page."""
        by, value = self._parse_locator(locator)
        wait_time = timeout or EXPLICIT_WAIT
        try:
            element = WebDriverWait(self.driver, wait_time).until(
                EC.visibility_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            log.error(f"Visible element NOT found: {by} = '{value}'")
            raise

    def find_elements(self, locator):
        """Find all matching elements."""
        by, value = self._parse_locator(locator)
        elements = self.wait.until(
            EC.presence_of_all_elements_located((by, value))
        )
        return elements

    # ================================================================
    # OVERLAY / BACKDROP HELPERS
    # ================================================================

    def dismiss_open_overlays(self):
        """
        Press Escape if any Angular CDK overlay backdrop is open.
        Waits for it to fully disappear before returning.
        This prevents ElementClickInterceptedException when a mat-select
        panel or dropdown is left open from a prior action.
        """
        try:
            backdrops = self.driver.find_elements(
                By.CSS_SELECTOR, ".cdk-overlay-backdrop-showing"
            )
            if backdrops:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                WebDriverWait(self.driver, 5).until(
                    EC.invisibility_of_element_located(
                        (By.CSS_SELECTOR, ".cdk-overlay-backdrop-showing")
                    )
                )
                log.info("Dismissed open CDK overlay backdrop")
                time.sleep(0.2)  # brief settle after animation
        except Exception:
            pass  # overlay was already gone or dismiss had no effect

    def wait_for_overlay_gone(self, timeout=10):
        """
        Wait until ALL CDK overlay backdrops (select panels, dialogs)
        have disappeared from the DOM.
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, ".cdk-overlay-backdrop-showing")
                )
            )
        except TimeoutException:
            log.warning("Overlay backdrop did not disappear within timeout")

    # ================================================================
    # ELEMENT INTERACTIONS
    # ================================================================

    def click(self, locator):
        """
        Wait for element to be clickable, then click it.

        Fallback chain:
          1. Normal .click()
          2. Dismiss any blocking CDK overlay, then retry .click()
          3. JavaScript click as last resort
        """
        element = self.find_clickable_element(locator)
        try:
            element.click()
            log.info(f"Clicked: {locator}")
        except ElementClickInterceptedException:
            # Step 1: try dismissing any open overlay (mat-select panel, backdrop)
            self.dismiss_open_overlays()
            try:
                # Re-fetch element after overlay dismissal
                element = self.find_clickable_element(locator)
                element.click()
                log.info(f"Clicked (after overlay dismiss): {locator}")
            except ElementClickInterceptedException:
                # Step 2: scroll into view and JS-click as final fallback
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", element
                )
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", element)
                log.info(f"Clicked (JS fallback): {locator}")

    def click_with_retry(self, locator, max_retries=3):
        """Click with retry logic for flaky elements."""
        for attempt in range(1, max_retries + 1):
            try:
                self.click(locator)
                return
            except (ElementClickInterceptedException,
                    StaleElementReferenceException) as e:
                log.warning(f"Click attempt {attempt} failed: {e}")
                time.sleep(1)
        raise Exception(f"Failed to click {locator} after {max_retries} attempts")

    def type_text(self, locator, text, clear_first=True):
        """
        Type text into an input field.
        Tries standard Selenium first; on InvalidElementStateException,
        falls back to JavaScript-based clearing and typing (for Angular
        reactive form controls that block .clear()).
        """
        element = self.find_visible_element(locator)
        try:
            if clear_first:
                element.clear()
            element.send_keys(text)
            log.info(f"Typed '{text}' into: {locator}")
        except InvalidElementStateException:
            # Angular reactive form input — use JS fallback
            log.info(f"Standard clear/send_keys failed, using JS fallback for: {locator}")
            self.js_type_text(locator, text, clear_first=clear_first)

    def js_type_text(self, locator, text, clear_first=True):
        """
        JavaScript-based type for Angular reactive form inputs.
        Standard Selenium .clear() throws InvalidElementStateException
        on Angular Material inputs. This method:
          1. Clears value via JS (using the native setter to bypass Angular)
          2. Dispatches 'input' + 'change' events so Angular detects the change
          3. Sets the new value via JS
          4. Dispatches events again so Angular picks up the new value
        """
        element = self.find_visible_element(locator)
        script = """
        var el = arguments[0];
        var newText = arguments[1];
        var shouldClear = arguments[2];
        var nativeSet = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;
        var nativeSetArea = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value'
        );
        if (nativeSetArea) { nativeSetArea = nativeSetArea.set; }

        var setter = el.tagName === 'TEXTAREA' && nativeSetArea
                     ? nativeSetArea : nativeSet;

        if (shouldClear) {
            setter.call(el, '');
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }
        setter.call(el, newText);
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        """
        self.driver.execute_script(script, element, str(text), clear_first)
        log.info(f"JS-typed '{text}' into: {locator}")

    def clear_field(self, locator):
        """Clear the text from an input field.
        Falls back to JS clearing for Angular reactive form controls.
        """
        element = self.find_visible_element(locator)
        try:
            element.clear()
            log.info(f"Cleared field: {locator}")
        except InvalidElementStateException:
            self.js_type_text(locator, "", clear_first=True)
            log.info(f"Cleared field (JS fallback): {locator}")

    def press_enter(self, locator):
        """Press Enter key on a specific element."""
        element = self.find_visible_element(locator)
        element.send_keys(Keys.ENTER)
        log.info(f"Pressed Enter on: {locator}")

    # ================================================================
    # ELEMENT STATE CHECKS
    # ================================================================

    def is_displayed(self, locator, timeout=5):
        """Check if element is visible (returns True/False)."""
        by, value = self._parse_locator(locator)
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def is_present(self, locator, timeout=5):
        """Check if element exists in DOM (may not be visible)."""
        by, value = self._parse_locator(locator)
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def is_enabled(self, locator):
        """Check if element is enabled (not disabled)."""
        element = self.find_element(locator)
        return element.is_enabled()

    def is_selected(self, locator):
        """Check if checkbox/radio is selected."""
        element = self.find_element(locator)
        return element.is_selected()

    def get_text(self, locator):
        """Get the visible text of an element."""
        element = self.find_visible_element(locator)
        text = element.text
        log.info(f"Got text: '{text}' from {locator}")
        return text

    def get_attribute(self, locator, attribute):
        """Get the value of an element attribute."""
        element = self.find_element(locator)
        value = element.get_attribute(attribute)
        log.info(f"Got attribute '{attribute}'='{value}' from {locator}")
        return value

    def get_value(self, locator):
        """Get the 'value' attribute of an input field."""
        return self.get_attribute(locator, "value")

    # ================================================================
    # WAIT HELPERS
    # ================================================================

    def wait_for_visible(self, locator, timeout=None):
        """Wait until element becomes visible."""
        wait_time = timeout or EXPLICIT_WAIT
        by, value = self._parse_locator(locator)
        WebDriverWait(self.driver, wait_time).until(
            EC.visibility_of_element_located((by, value))
        )

    def wait_for_invisible(self, locator, timeout=None):
        """Wait until element disappears or becomes invisible."""
        wait_time = timeout or EXPLICIT_WAIT
        by, value = self._parse_locator(locator)
        WebDriverWait(self.driver, wait_time).until(
            EC.invisibility_of_element_located((by, value))
        )

    def wait_for_clickable(self, locator, timeout=None):
        """Wait until element is clickable."""
        wait_time = timeout or EXPLICIT_WAIT
        by, value = self._parse_locator(locator)
        WebDriverWait(self.driver, wait_time).until(
            EC.element_to_be_clickable((by, value))
        )

    def wait_seconds(self, seconds):
        """Hard wait (use sparingly — prefer explicit waits)."""
        time.sleep(seconds)

    # ================================================================
    # SCREENSHOTS
    # ================================================================

    def take_screenshot(self, test_name="screenshot"):
        """Capture a screenshot and save to screenshots/ directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_name}_{timestamp}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)

        # Ensure directory exists
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)

        self.driver.save_screenshot(filepath)
        log.info(f"Screenshot saved: {filepath}")
        return filepath

    # ================================================================
    # PAGE NAVIGATION
    # ================================================================

    def navigate_to(self, url):
        """Navigate to a specific URL."""
        log.info(f"Navigating to: {url}")
        self.driver.get(url)

    def get_current_url(self):
        """Get the current page URL."""
        return self.driver.current_url

    def get_page_title(self):
        """Get the current page title."""
        return self.driver.title

    def refresh_page(self):
        """Refresh the current page."""
        self.driver.refresh()
        log.info("Page refreshed")

    # ================================================================
    # JAVASCRIPT UTILITIES
    # ================================================================

    def scroll_to_element(self, locator):
        """Scroll the page until the element is in view."""
        element = self.find_element(locator)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )

    def scroll_to_top(self):
        """Scroll to the top of the page."""
        self.driver.execute_script("window.scrollTo(0, 0);")

    def scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

    def highlight_element(self, locator, duration=1):
        """Highlight an element briefly (useful for debugging)."""
        element = self.find_element(locator)
        self.driver.execute_script(
            "arguments[0].style.border = '3px solid red';", element
        )
        time.sleep(duration)
        self.driver.execute_script(
            "arguments[0].style.border = '';", element
        )

    # ================================================================
    # ALERT HANDLING
    # ================================================================

    def accept_alert(self):
        """Accept (OK) a JavaScript alert/prompt/confirm."""
        alert = self.wait.until(EC.alert_is_present())
        alert.accept()
        log.info("Accepted alert")

    def dismiss_alert(self):
        """Dismiss (Cancel) a JavaScript alert/prompt/confirm."""
        alert = self.wait.until(EC.alert_is_present())
        alert.dismiss()
        log.info("Dismissed alert")

    def get_alert_text(self):
        """Get the text from a JavaScript alert/prompt/confirm."""
        alert = self.wait.until(EC.alert_is_present())
        return alert.text

    # ================================================================
    # INTERNAL HELPERS
    # ================================================================

    def _parse_locator(self, locator):
        """
        Parse locator tuple into (By, value).
        Supports:
            ("css", "#id")          -> By.CSS_SELECTOR
            ("xpath", "//div")      -> By.XPATH
            ("id", "username")      -> By.ID
            ("name", "email")       -> By.NAME
            ("class", "btn")        -> By.CLASS_NAME
            ("tag", "input")        -> By.TAG_NAME
            ("link_text", "Click")  -> By.LINK_TEXT
            ("partial", "Click")    -> By.PARTIAL_LINK_TEXT
        """
        strategy_map = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "tag": By.TAG_NAME,
            "link_text": By.LINK_TEXT,
            "partial": By.PARTIAL_LINK_TEXT,
        }

        if not isinstance(locator, tuple) or len(locator) != 2:
            raise ValueError(
                f"Locator must be a tuple: ('strategy', 'value'). "
                f"Got: {locator}"
            )

        strategy, value = locator
        strategy = strategy.lower()

        if strategy not in strategy_map:
            raise ValueError(
                f"Unknown locator strategy: '{strategy}'. "
                f"Supported: {list(strategy_map.keys())}"
            )

        return strategy_map[strategy], value