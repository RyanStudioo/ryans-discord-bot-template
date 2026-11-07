"""Permission decorators for application (slash) commands.

Every decorator returns an ``app_commands.check`` predicate, so they stack with
other application-command decorators and work on both commands and groups.

Example::

    @app_commands.command(name="purge")
    @is_mod()
    async def purge(interaction: discord.Interaction, amount: int):
        ...
"""

from __future__ import annotations

import discord
from discord import app_commands

MODERATOR_PERMISSIONS = (
    "manage_messages",
    "kick_members",
    "ban_members",
    "moderate_members",
    "manage_threads",
    "manage_channels",
)


class OwnerOnly(app_commands.CheckFailure):
    """Raised when a command is used by someone other than the bot owner."""


class AdminOnly(app_commands.CheckFailure):
    """Raised when a command is used without the Administrator permission."""


class ModOnly(app_commands.CheckFailure):
    """Raised when a command is used without moderator permissions."""


class MissingPermissions(app_commands.CheckFailure):
    """Raised when a command is used without one or more specific permissions."""

    def __init__(self, permissions: set[str]):
        self.permissions = permissions
        joined = ", ".join(f"`{name}`" for name in sorted(permissions))
        super().__init__(f"You are missing the following permissions: {joined}.")


def _member_permissions(interaction: discord.Interaction) -> discord.Permissions | None:
    """Return the invoker's guild permissions, or ``None`` in DMs."""
    if interaction.guild is None:
        return None

    member = interaction.user
    if not isinstance(member, discord.Member):
        return None

    return member.guild_permissions


def is_owner():
    """Only allow the bot owner (or application team members)."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if not await interaction.client.is_owner(interaction.user):
            raise OwnerOnly("This command can only be used by the bot owner.")
        return True

    return app_commands.check(predicate)


def is_admin():
    """Only allow members with the Administrator permission."""

    async def predicate(interaction: discord.Interaction) -> bool:
        permissions = _member_permissions(interaction)
        if permissions is None or not permissions.administrator:
            raise AdminOnly("This command requires the `Administrator` permission.")
        return True

    return app_commands.check(predicate)


def is_mod():
    """Allow administrators and members with any moderator permission."""

    async def predicate(interaction: discord.Interaction) -> bool:
        permissions = _member_permissions(interaction)
        if permissions is None:
            raise ModOnly("This command can only be used inside a server.")
        if permissions.administrator:
            return True
        if not any(getattr(permissions, name, False) for name in MODERATOR_PERMISSIONS):
            raise ModOnly("This command requires moderator permissions.")
        return True

    return app_commands.check(predicate)


def has_permissions(**required: bool):
    """Require an arbitrary set of named permissions.

    Example::

        @has_permissions(manage_guild=True, manage_roles=True)
    """

    required_names = {name for name, enabled in required.items() if enabled}

    async def predicate(interaction: discord.Interaction) -> bool:
        permissions = _member_permissions(interaction)
        missing = {
            name
            for name in required_names
            if permissions is None or not getattr(permissions, name, False)
        }
        if missing:
            raise MissingPermissions(missing)
        return True

    return app_commands.check(predicate)
