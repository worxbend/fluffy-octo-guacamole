"""Logging bootstrap helpers."""

from __future__ import annotations

import logging

import structlog

from frostfire.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(message)s",
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
