"""Centralized logging configuration for the RAG ingestion pipeline."""
import sys
import logging
from pathlib import Path

from config.settings import settings


def setup_logging() -> None:
    """Configure the root logger for the entire pipeline.

    Sets up both console (stdout) and file handlers with structured output.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level.upper())
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    file_handler.setLevel(settings.log_level.upper())
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Reduce noisy loggers
    for logger_name in ("opensearchpy", "urllib3", "watchdog", "PIL"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        f"Logging initialized (level={settings.log_level}, file={settings.log_file})"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: The logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)