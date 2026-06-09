"""
browser_utils.py
----------------
Browser setup, configuration, and management utilities.
Uses Selenium's built-in SeleniumManager (NO webdriver-manager needed).
"""

import os
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

from config import BROWSER, HEADLESS, PAGE_LOAD_TIMEOUT, IMPLICIT_WAIT
from common.logger import log


def get_chrome_driver():
    """Create and configure Google Chrome WebDriver."""
    log.info("Setting up Chrome browser...")

    options = ChromeOptions()

    # Headless mode
    if HEADLESS:
        options.add_argument("--headless=new")
        log.info("Headless mode: ON")

    # Fresh temp profile — no saved creds, no autofill memory, clean slate every run
    temp_profile = tempfile.mkdtemp(prefix="rhythm_test_chrome_")
    options.add_argument(f"--user-data-dir={temp_profile}")

    # Common options for stability
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-autofill")
    options.add_argument("--remote-allow-origins=*")

    # Handle "Chrome is being controlled by automated test software" banner
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Disable autofill — belt and suspenders
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "autofill.profile_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    # Selenium 4.41+ built-in SeleniumManager — no webdriver-manager needed
    driver = webdriver.Chrome(options=options)

    # Set timeouts
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(IMPLICIT_WAIT)

    log.info("Chrome browser launched successfully (fresh profile)")
    return driver


def get_edge_driver():
    """Create and configure Microsoft Edge WebDriver."""
    log.info("Setting up Edge browser...")

    options = EdgeOptions()

    if HEADLESS:
        options.add_argument("--headless=new")
        log.info("Headless mode: ON")

    # Fresh temp profile — no saved creds, no autofill memory, clean slate every run
    temp_profile = tempfile.mkdtemp(prefix="rhythm_test_edge_")
    options.add_argument(f"--user-data-dir={temp_profile}")

    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-autofill")
    options.add_argument("--remote-allow-origins=*")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Disable autofill
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "autofill.profile_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    # Selenium 4.41+ built-in SeleniumManager
    driver = webdriver.Edge(options=options)

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(IMPLICIT_WAIT)

    log.info("Edge browser launched successfully (fresh profile)")
    return driver


def get_driver():
    """
    Factory method — returns the correct driver based on config.
    Reads BROWSER from .env or config.py.
    Supported: 'chrome', 'edge'
    """
    browser = BROWSER.lower()

    if browser == "chrome":
        return get_chrome_driver()
    elif browser == "edge":
        return get_edge_driver()
    else:
        log.error(f"Unsupported browser: {browser}. Use 'chrome' or 'edge'.")
        raise ValueError(f"Unsupported browser: {browser}")


def quit_driver(driver):
    """Safely quit the browser driver."""
    if driver:
        try:
            driver.quit()
            log.info("Browser closed.")
        except Exception:
            pass