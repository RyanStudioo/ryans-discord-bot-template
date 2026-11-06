import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import discord

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """Configure console and rotating file logging for the bot and its cogs."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    level = getattr(logging, log_level, logging.INFO)

    # Console output, configured on the root logger so our cogs are included.
    discord.utils.setup_logging(
        handler=logging.StreamHandler(),
        formatter=formatter,
        level=level,
        root=True,
    )
    root_logger = logging.getLogger()

    # Rotating file output, capped at ~25 MB (5 MB x 5 files).
    file_handler = RotatingFileHandler(
        log_dir / "bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    root_logger.info(
        "Logging initialised (level=%s, directory=%s)",
        log_level,
        log_dir.resolve(),
    )
