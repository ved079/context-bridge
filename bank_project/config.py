"""
config.py
---------
Central configuration for PACS Automation Project.
All URLs, timeouts, paths, and settings are defined here.
Other modules import from this file — change once, reflects everywhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()




# ============================================================
# RHYTHMERP APPLICATION
# ============================================================
RHYTHMERP_BASE_URL = "https://rhythmerp.algorhythms.in"
RHYTHMERP_LOGIN_URL = f"{RHYTHMERP_BASE_URL}/#/authentication/signin"
RHYTHMERP_LOGIN_URL = f"{RHYTHMERP_BASE_URL}/#/authentication/signin"
LOGIN_URL = RHYTHMERP_LOGIN_URL    # <-- add this line
COMPANY_ONBOARDING_URL = f"{RHYTHMERP_BASE_URL}/#/dynamic-screens/Company%20Onboarding"
RHYTHMERP_FORGOT_PASSWORD_URL = f"{RHYTHMERP_BASE_URL}/#/authentication/forgot-password"



# ============================================================
# RHYTHMERP LOGIN CREDENTIALS
# ============================================================
RHYTHMERP_EMAIL = "test@gmail.com"
RHYTHMERP_PASSWORD = "Test@2526270"
RHYTHMERP_FACILITY = ""  # blank text dropdown — click by index
NEW_RHYTHMERP_EMAIL = "kedar@1"
NEW_RHYTHMERP_PASSWORD = "Neo@123456789"
NEW_RHYTHMERP_FACILITY = ""



# ============================================================
# FORGOT PASSWORD CREDENTIALS (loaded from .env)
# ============================================================
FP_EMAIL = os.getenv("FP_EMAIL", "")
FP_CURRENT_PASSWORD = os.getenv("FP_CURRENT_PASSWORD", "")
FP_NEW_PASSWORD = os.getenv("FP_NEW_PASSWORD", "")
FP_ALT_PASSWORD = os.getenv("FP_ALT_PASSWORD", "")
FP_USERNAME = os.getenv("FP_USERNAME", "")
FP_TENANT = os.getenv("FP_TENANT", "")
FP_OLD_PASSWORDS = [
    os.getenv("FP_OLD_PASSWORD_1", ""),
    os.getenv("FP_OLD_PASSWORD_2", ""),
    os.getenv("FP_OLD_PASSWORD_3", ""),
]


# ============================================================
# RHYTHMERP FORGOT PASSWORD CREDENTIALS
# ============================================================
RHYTHMERP_FP_EMAIL = "vedant@rhythmflows.com"
RHYTHMERP_FP_USERNAME = "test@gmail.com"
RHYTHMERP_FP_TENANT = ""  # blank text — click by index
RHYTHMERP_FP_CURRENT_PASSWORD = "Test@1315378"
RHYTHMERP_FP_NEW_PASSWORD = ""
RHYTHMERP_FP_ALT_PASSWORD = ""
RHYTHMERP_FP_DEFAULT_PASSWORD = "Test@2526270"   # cleanup target — reset back after tests
RHYTHMERP_FP_OLD_PASSWORDS = ["", "", ""]


# ============================================================
# BROWSER SETTINGS
# ============================================================
BROWSER = os.getenv("BROWSER", "chrome").lower()  # "chrome" or "edge"
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"


# ============================================================
# TIMEOUTS (in seconds)
# ============================================================
EXPLICIT_WAIT = int(os.getenv("EXPLICIT_WAIT", "15"))
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))
IMPLICIT_WAIT = 5


# ============================================================
# DIRECTORY PATHS (relative to project root)
# ============================================================
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "pages", "login_screens", "screenshots")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "pages", "login_screens", "reports")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Ensure directories exist
for directory in [SCREENSHOT_DIR, REPORT_DIR, DATA_DIR]:
    os.makedirs(directory, exist_ok=True)
