"""Embed builders shared between cogs."""

from __future__ import annotations

import math
from collections.abc import Iterable

import discord
from discord import app_commands

HELP_COLOR = discord.Color.blurple()
SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
WARNING_COLOR = discord.Color.orange()
INFO_COLOR = discord.Color.blurple()
COMMANDS_PER_PAGE = 8


def _status_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


def success(description: str, *, title: str = "Success") -> discord.Embed:
    """Green embed for a completed action."""
    return _status_embed(title, description, SUCCESS_COLOR)


def error(description: str, *, title: str = "Error") -> discord.Embed:
    """Red embed for a failed action.

    ``title`` names the type of error, e.g. ``"Permission denied"``.
    """
    return _status_embed(title, description, ERROR_COLOR)


def warning(description: str, *, title: str = "Warning") -> discord.Embed:
    """Orange embed for something the user should notice."""
    return _status_embed(title, description, WARNING_COLOR)


def info(description: str, *, title: str = "Info") -> discord.Embed:
    """Blue embed for neutral information."""
    return _status_embed(title, description, INFO_COLOR)


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
