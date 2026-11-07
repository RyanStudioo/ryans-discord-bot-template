"""Permission decorators for application (slash) commands.

Every decorator returns an ``app_commands.check`` predicate, so they stack with
other application-command decorators and work on both commands and groups.
``is_bot_owner_prefix()`` is the exception: it guards text (prefix) commands and
returns a ``commands.check`` instead, since they never collect app-command checks.

Example::

    @app_commands.command(name="purge")
    @is_mod()
    async def purge(interaction: discord.Interaction, amount: int):
        ...
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

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


def is_bot_owner():
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


def is_bot_owner_prefix():
    """Only allow the bot owner, for text (prefix) commands such as ``!sync``.

    Text commands do not collect ``app_commands.check`` predicates, so this
    mirrors ``is_bot_owner()`` as a ``commands.check`` that raises ``OwnerOnly``.

    Example::

        @commands.command(name="sync")
        @is_bot_owner_prefix()
        async def sync(ctx: commands.Context, option: str = ""):
            ...
    """

    async def predicate(ctx: commands.Context) -> bool:
        if not await ctx.bot.is_owner(ctx.author):
            raise OwnerOnly("This command can only be used by the bot owner.")
        return True

    return commands.check(predicate)
