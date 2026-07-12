"""
ResearchAI — Centralized Logging
Provides a structured, colour-coded logger for all modules.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Return a named logger that writes to both stdout and a rotating
    file at data/logs/researchai.log.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(console)

    # File handler — 10 MB max, keep 5 backups
    file_handler = RotatingFileHandler(
        LOG_DIR / "researchai.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
