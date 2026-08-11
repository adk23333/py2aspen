import sys

from loguru import logger

default_format: str = (
    "<g>{time:MM-DD HH:mm:ss.SSS}</g> "
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}</u></c> | "
    # "<c>{function}:{line}</c>| "
    "{message}"
)

def set_level(level: str) -> None:
    """Replace the stdout handler with the given minimum log level."""
    logger.remove()
    logger.add(sys.stdout, level=level, format=default_format)

set_level("INFO")