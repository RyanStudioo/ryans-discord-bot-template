"""Command tree with friendly error handling for checks and unhandled errors."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from src.utils.checks import AdminOnly, MissingPermissions, ModOnly, OwnerOnly

logger = logging.getLogger(__name__)

CHECK_FAILURES = (OwnerOnly, AdminOnly, ModOnly, MissingPermissions)


class BotTree(app_commands.CommandTree):
    """Application command tree that responds to failures with a clear message."""

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
        /,
    ) -> None:
        command = interaction.command
        name = command.qualified_name if command is not None else "unknown"

        # A local error handler (or the command itself) already replied.
        if interaction.response.is_done():
            return

        if isinstance(error, CHECK_FAILURES):
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True,
            )
            return

        logger.error("Unhandled error in command '%s'", name, exc_info=error)
        await interaction.response.send_message(
            "Something went wrong while running this command.",
            ephemeral=True,
        )
