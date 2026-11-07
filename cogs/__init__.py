import logging

from discord.ext import commands

from src.utils.constants import COGS_PATH, IGNORED_COGS

logger = logging.getLogger(__name__)


async def load_cogs(bot: commands.Bot) -> None:
    """Load every cog in this package, logging and skipping any that fail.

    A cog can be a single ``.py`` file or a folder. For a folder, its
    ``__init__.py`` is imported and must expose a ``setup()`` function.
    """
    for entry in sorted(COGS_PATH.iterdir()):
        if entry.name in IGNORED_COGS or entry.name.startswith("_"):
            continue

        if entry.is_dir():
            if not (entry / "__init__.py").is_file():
                continue
            extension = f"cogs.{entry.name}"
        elif entry.suffix == ".py":
            extension = f"cogs.{entry.stem}"
        else:
            continue
        try:
            await bot.load_extension(extension)
        except Exception:
            logger.exception("Failed to load extension '%s'", extension)
        else:
            logger.info("Loaded extension '%s'", extension)
