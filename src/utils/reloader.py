"""Watch the cogs directory and reload only the extension that changed."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from discord.ext import commands
from watchfiles import Change, awatch

from src.utils.constants import COGS_PATH, IGNORED_COGS

logger = logging.getLogger(__name__)

WATCHED_CHANGES = {Change.added, Change.modified}


def _auto_reload_enabled() -> bool:
    value = os.getenv("AUTO_RELOAD", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


class CogReloader:
    """Background task that hot-reloads cogs when their source files change."""

    def __init__(self, bot: commands.Bot, cogs_path: Path = COGS_PATH):
        self.bot = bot
        self.cogs_path = cogs_path
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if not _auto_reload_enabled():
            logger.info("Cog auto-reload is disabled (AUTO_RELOAD=false)")
            return
        if self._task is not None:
            return

        self._task = asyncio.create_task(self._watch(), name="cog-reloader")
        logger.info("Watching '%s' for cog changes", self.cogs_path)

    async def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
            logger.info("Stopped watching '%s' for cog changes", self.cogs_path)

    async def _watch(self) -> None:
        async for changes in awatch(self.cogs_path, debounce=500):
            for change, raw_path in changes:
                await self._handle_change(change, Path(raw_path))

    async def _handle_change(self, change: Change, path: Path) -> None:
        if change not in WATCHED_CHANGES:
            return
        if path.suffix != ".py" or path.name.startswith("_"):
            return
        if path.name in IGNORED_COGS or "__pycache__" in path.parts:
            return

        extension = f"cogs.{path.stem}"
        already_loaded = extension in self.bot.extensions

        try:
            if already_loaded:
                await self.bot.reload_extension(extension)
            else:
                await self.bot.load_extension(extension)
        except Exception:
            logger.exception(
                "Failed to %s extension '%s' after change in '%s'",
                "reload" if already_loaded else "load",
                extension,
                path.name,
            )
        else:
            logger.info(
                "%s extension '%s' after change in '%s'",
                "Reloaded" if already_loaded else "Loaded",
                extension,
                path.name,
            )
