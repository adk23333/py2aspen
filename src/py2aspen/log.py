import sys

from loguru import logger

default_format: str = (
    "<g>{time:MM-DD HH:mm:ss.SSS}</g> "
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}</u></c> | "
    # "<c>{function}:{line}</c>| "
    "{message}"
)

logger.remove(0)  # 移除默认的 stderr 输出

logger.add(
    sys.stdout,
    level="INFO",
    format=default_format,
)