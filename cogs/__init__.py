import logging

from discord.ext import commands

from src.utils.constants import COGS_PATH, IGNORED_COGS

logger = logging.getLogger(__name__)


async def load_cogs(bot: commands.Bot) -> None:
    """Load every cog in this package, logging and skipping any that fail."""
    for file in sorted(COGS_PATH.glob("*.py")):
        if file.name in IGNORED_COGS or file.name.startswith("_"):
            continue

        extension = f"cogs.{file.stem}"
        try:
            await bot.load_extension(extension)
        except Exception:
            logger.exception("Failed to load extension '%s'", extension)
        else:
            logger.info("Loaded extension '%s'", extension)
