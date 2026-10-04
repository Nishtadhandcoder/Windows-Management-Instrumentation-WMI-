"""
Structured logging configuration with console output and rotating file handler.
"""
import sys
import logging
from logging.handlers import RotatingFileHandler
from config.settings import settings


def setup_logging() -> None:
    """Configures root logging with standard formatters and handlers."""
    settings.ensure_directories()

    log_level = getattr(logging, settings.log_level, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if already configured
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console stream handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler (10MB max, up to 5 backups)
    try:
        file_handler = RotatingFileHandler(
            filename=str(settings.log_file_path),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as exc:
        console_handler.handle(
            logging.LogRecord(
                name="config.logging",
                level=logging.WARNING,
                pathname=__file__,
                lineno=45,
                msg=f"Could not initialize file log handler at {settings.log_file_path}: {exc}",
                args=(),
                exc_info=None,
            )
        )


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger instance."""
    return logging.getLogger(name)


# Automatically initialize logging upon import
setup_logging()
