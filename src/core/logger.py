import logging
import sys
from logging.config import dictConfig

from src.core.config import config

LOG_FORMATTERS = {
    "CONSOLE": (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    ),
    "JSON": "%(message)s",  # TODO
}

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # Важно: не отключать сторонние логгеры полностью
    "formatters": {
        "default": {
            "format": LOG_FORMATTERS.get(config.log_format, LOG_FORMATTERS["CONSOLE"]),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "default",
            "level": config.log_level,
        },
    },
    "root": {
        "level": config.log_level,
        "handlers": ["console"],
    },
    "loggers": {
        "app": {"level": getattr(config, 'log_level', 'INFO')},
        "fastapi": {"level": "INFO"},
        "uvicorn": {"level": "INFO"},
        "uvicorn.access": {"level": "WARNING"},
        "uvicorn.error": {"level": "INFO"},
        "sqlalchemy": {"level": "WARNING"},
        "alembic": {"level": "INFO"},
        "httpx": {"level": "WARNING"},
        "asyncio": {"level": "WARNING"},
    },
}

def setup_logging():
    dictConfig(LOGGING_CONFIG)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)