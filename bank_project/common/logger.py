"""
logger.py - Stub logger for test execution environment.
Matches the interface of the project's actual logger:
  log.info(), log.warning(), log.error(), log.step(), log.separator()
"""

import logging
import os
import sys
from datetime import datetime


class Logger:
    """Minimal logger matching the project's common.logger interface."""

    def __init__(self, name="RhythmERP"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            fmt = logging.Formatter(
                "%(asctime)s [%(levelname)-5s] %(message)s",
                datefmt="%H:%M:%S",
            )
            handler.setFormatter(fmt)
            self.logger.addHandler(handler)
        self.handlers = []

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def step(self, step_num, description):
        self.info(f">>> STEP {step_num}: {description}")

    def separator(self):
        self.info("=" * 60)


log = Logger()
