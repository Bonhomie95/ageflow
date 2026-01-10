from __future__ import annotations

from loguru import logger


def get_logger(name: str = "ageflow"):
    return logger.bind(scope=name)
