"""Centralized logging configuration for the LLM Council backend.

Logs to stdout (captured by journald under the systemd deployment). The level
is controlled by the LOG_LEVEL environment variable (default INFO). Call
configure_logging() once at startup, then use logging.getLogger(__name__) in
each module.
"""

import logging
import os

_CONFIGURED = False


def configure_logging() -> None:
    """Configure the root logger once. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _CONFIGURED = True
