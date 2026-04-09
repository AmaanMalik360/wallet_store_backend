import logging
import logging.config
from pathlib import Path

from core.config import settings


LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE_PATH = LOG_DIR / "server-logs.log"


def get_logging_config() -> dict:
    level = logging.DEBUG if settings.debug else logging.INFO

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "standard",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": level,
                "formatter": "standard",
                "filename": str(LOG_FILE_PATH),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": level,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console", "file"],
                "level": level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": level,
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": [],
                "level": logging.WARNING,
                "propagate": False,
            },
        },
    }


def setup_logging() -> None:
    """Configure global logging for the application."""

    config = get_logging_config()
    logging.config.dictConfig(config)
