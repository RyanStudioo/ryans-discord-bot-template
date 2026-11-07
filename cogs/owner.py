"""Owner-only operational commands, issued as text messages with the ``!`` prefix.

Text commands never show up in the auto-generated ``/help``, which is intended
here: these are bot ops, not user features. Note that loading or reloading a
cog only updates the in-memory command tree, so run ``!sync`` afterwards when
a cog adds or changes slash commands.
"""

import logging
from collections.abc import Awaitable, Callable

from discord.ext import commands

from src.utils.checks import OwnerOnly, is_bot_owner_prefix
from src.utils.constants import COGS_PATH, IGNORED_COGS

logger = logging.getLogger(__name__)

EXTENSION_PREFIX = "cogs."
OWNER_EXTENSION = f"{EXTENSION_PREFIX}owner"


def _extension_name(name: str) -> str:
    """Map a user-supplied cog name (``owner``) to its full extension (``cogs.owner``)."""
    name = name.removesuffix(".py")
    if name.startswith(EXTENSION_PREFIX):
        return name
    return f"{EXTENSION_PREFIX}{name}"


class Owner(commands.Cog):
    """Operational commands for the bot owner, invoked with the ``!`` prefix."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _available_cogs(self) -> list[str]:
        """Discover every loadable cog name, mirroring the auto-loader's rules."""
        names: list[str] = []
        for entry in sorted(COGS_PATH.iterdir()):
            if entry.name in IGNORED_COGS or entry.name.startswith("_"):
                continue

            if entry.is_dir():
                if (entry / "__init__.py").is_file():
                    names.append(entry.name)
            elif entry.suffix == ".py":
                names.append(entry.stem)

        return names

    @commands.command(
        name="cogs",
        help="List every cog on disk and whether it is loaded.",
    )
    @is_bot_owner_prefix()
    async def cogs(self, ctx: commands.Context):
        available = self._available_cogs()
        loaded = [name for name in available if f"{EXTENSION_PREFIX}{name}" in self.bot.extensions]
        not_loaded = [name for name in available if name not in loaded]

        def fmt(names: list[str]) -> str:
            return ", ".join(f"`{name}`" for name in names) if names else "none"

        await ctx.send(f"Loaded: {fmt(loaded)}\nNot loaded: {fmt(not_loaded)}")

    @commands.command(
        name="sync",
        help=(
            "Re-sync the slash command tree with Discord. Options: `global` (default), "
            "`guild` to copy global commands to this server for fast testing, or "
            "`clear` to empty this server's copy (use after renaming a command)."
        ),
    )
    @is_bot_owner_prefix()
    async def sync(self, ctx: commands.Context, option: str = ""):
        tree = self.bot.tree

        if option in {"guild", "clear"}:
            if ctx.guild is None:
                await ctx.send(
                    "`!sync guild` and `!sync clear` must be used inside a server.",
                    delete_after=10,
                )
                return

            if option == "guild":
                tree.copy_global_to(guild=ctx.guild)
            else:
                tree.clear_commands(guild=ctx.guild)

            synced = await tree.sync(guild=ctx.guild)
            verb = "Copied global commands and" if option == "guild" else "Cleared"
            await ctx.send(f"{verb} synced {len(synced)} command(s) to **{ctx.guild.name}**.")
            logger.info("!sync %s run by %s in guild %s", option, ctx.author, ctx.guild.id)
            return

        if option in {"", "global"}:
            synced = await tree.sync()
            await ctx.send(f"Synced {len(synced)} global slash command(s).")
            logger.info("Global !sync run by %s", ctx.author)
            return

        await ctx.send(
            f"Unknown option `{option}`. Use `global` (default), `guild`, or `clear`.",
            delete_after=10,
        )

    @commands.command(
        name="load",
        help="Load a cog that is on disk but not loaded, e.g. `!load template_copy`.",
    )
    @is_bot_owner_prefix()
    async def load(self, ctx: commands.Context, name: str = ""):
        await self._manage_extension(ctx, "load", name)

    @commands.command(
        name="unload",
        help="Unload a loaded cog, e.g. `!unload ping`.",
    )
    @is_bot_owner_prefix()
    async def unload(self, ctx: commands.Context, name: str = ""):
        await self._manage_extension(ctx, "unload", name)

    @commands.command(
        name="reload",
        help="Reload a loaded cog, e.g. `!reload owner`.",
    )
    @is_bot_owner_prefix()
    async def reload(self, ctx: commands.Context, name: str = ""):
        await self._manage_extension(ctx, "reload", name)

    async def _manage_extension(self, ctx: commands.Context, action: str, name: str) -> None:
        if not name:
            await ctx.send(
                f"Usage: `!{action} <cog-name>` — run `!cogs` to see available names.",
                delete_after=10,
            )
            return

        extension = _extension_name(name)

        # Unloading this cog would take away !load / !shutdown until a restart.
        if action == "unload" and extension == OWNER_EXTENSION:
            await ctx.send(
                f"Refusing to unload `{OWNER_EXTENSION}` — use `!reload owner` instead.",
                delete_after=10,
            )
            return

        handlers: dict[str, Callable[[str], Awaitable[None]]] = {
            "load": self.bot.load_extension,
            "unload": self.bot.unload_extension,
            "reload": self.bot.reload_extension,
        }

        try:
            await handlers[action](extension)
        except commands.ExtensionNotFound:
            await ctx.send(f"No cog named `{name}` exists.", delete_after=10)
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f"`{extension}` is already loaded.", delete_after=10)
        except commands.ExtensionNotLoaded:
            await ctx.send(f"`{extension}` is not loaded. Try `!load {name}`.", delete_after=10)
        except commands.NoEntryPointError:
            await ctx.send(f"`{extension}` has no `setup()`, so it cannot be loaded.", delete_after=10)
        except Exception:
            logger.exception("Failed to %s extension '%s'", action, extension)
            await ctx.send(f"Failed to {action} `{extension}` — check `logs/bot.log`.")
        else:
            note = (
                "\nReminder: run `!sync` if this cog adds or changes slash commands."
                if action in {"load", "reload"}
                else ""
            )
            await ctx.send(f"{action.capitalize()}ed `{extension}`.{note}")
            logger.info("%sed '%s' (owner: %s)", action, extension, ctx.author)

    @commands.command(
        name="shutdown",
        help="Gracefully stop the bot process.",
    )
    @is_bot_owner_prefix()
    async def shutdown(self, ctx: commands.Context):
        await ctx.send("Shutting down. 👋")
        logger.info("Shutdown requested by %s", ctx.author)
        await self.bot.close()

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        command = ctx.command
        name = command.qualified_name if command is not None else "unknown"

        # app_commands.CheckFailure is unrelated to the commands one, so the
        # template's OwnerOnly must be matched explicitly.
        if isinstance(error, (OwnerOnly, commands.CheckFailure)):
            await ctx.send(str(error), delete_after=10)
            return

        logger.error("Unhandled error in command '!%s'", name, exc_info=error)
        await ctx.send("Something went wrong while running this command.", delete_after=10)


async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
