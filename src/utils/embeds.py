"""Embed builders shared between cogs."""

from __future__ import annotations

import math
from collections.abc import Iterable

import discord
from discord import app_commands

HELP_COLOR = discord.Color.blurple()
COMMANDS_PER_PAGE = 8


def _leaf_commands(
    command: app_commands.Command | app_commands.ContextMenu,
) -> list[app_commands.Command]:
    if not isinstance(command, app_commands.Command):
        return []

    if isinstance(command, app_commands.Group):
        leaves = [
            child
            for child in command.walk_commands()
            if not isinstance(child, app_commands.Group)
        ]
        return leaves or [command]

    return [command]


def collect_command_entries(
    commands: Iterable[app_commands.Command | app_commands.ContextMenu],
) -> list[tuple[str, str]]:
    """Flatten the command tree into ``(name, description)`` pairs."""
    entries: list[tuple[str, str]] = []
    for command in commands:
        for leaf in _leaf_commands(command):
            description = leaf.description
            if not description or description in {"…", "..."}:
                description = "No description provided."
            entries.append((leaf.qualified_name, description))
    return sorted(entries, key=lambda entry: entry[0].lower())


def build_help_pages(
    commands: Iterable[app_commands.Command | app_commands.ContextMenu],
    *,
    bot_name: str,
    per_page: int = COMMANDS_PER_PAGE,
) -> list[discord.Embed]:
    """Build one or more help embeds from the bot's application commands."""
    entries = collect_command_entries(commands)
    if not entries:
        entries = [("help", "No application commands are currently registered.")]

    total_pages = math.ceil(len(entries) / per_page)
    pages: list[discord.Embed] = []

    for page_index, start in enumerate(range(0, len(entries), per_page), start=1):
        embed = discord.Embed(
            title=f"{bot_name} Commands",
            description="Use a command by typing its name in the chat box.",
            color=HELP_COLOR,
        )
        for name, description in entries[start : start + per_page]:
            embed.add_field(name=f"/{name}", value=description, inline=False)
        embed.set_footer(
            text=f"Page {page_index}/{total_pages} • {len(entries)} commands"
        )
        pages.append(embed)

    return pages
