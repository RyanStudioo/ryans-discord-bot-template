# Migrating an Existing Bot to This Template

A guide for porting an existing discord.py bot into this repo's format. It
assumes the typical shape of an older bot: a single `bot.py`/`main.py` entry
point, a hand-maintained cog list, user commands as `!` prefix commands, and
ad-hoc permission and error handling.

Read first: [`ARCHITECTURE.md`](ARCHITECTURE.md) describes the target format in
detail; [`AGENTS.md`](AGENTS.md) lists the working rules. The short version of
the format:

- **`main.py` is the only entrypoint.** It builds the `Bot`, loads every cog,
  runs one global `tree.sync()`, and starts a `watchfiles` hot reloader.
- **`cogs/` is auto-discovered.** A cog is a `cogs/*.py` file or a
  `cogs/<name>/` folder with an `__init__.py`; both expose
  `async def setup(bot)`. No manual registration anywhere.
- **`src/utils/` is shared infrastructure**: permission checks, the command
  tree with error handling, logging, `/help` builder, paginator, constants.
- **User commands are slash commands only.** The `!` prefix is reserved for
  owner-only ops in `cogs/owner.py` and never shows in `/help`.

---

## 1. Before you start

1. **Discord Developer Portal**: with `Intents.all()` the bot needs the
   privileged intents **Message Content**, **Server Members**, and **Presence**
   enabled for the application, or login fails with
   `PrivilegedIntentsRequired`.
2. **Tooling**: install Python ≥ 3.13 and `uv`, then from the repo root:

   ```sh
   uv sync                 # install dependencies (creates .venv)
   cp .env.example .env    # then set DISCORD_TOKEN
   ```

3. **Dependencies** you need beyond the template's: add with `uv add <package>`
   (updates `pyproject.toml` and `uv.lock`). Never `pip install` and never
   hand-edit `uv.lock`.

## 2. Inventory your existing bot

Write down — it becomes your migration TODO list:

- Entrypoint file(s) and how cogs are registered today (manual
  `load_extension` list? `setup_hook`? on_ready registration?).
- Full command list: prefix commands, plus any slash commands already
  registered (avoid double-registering).
- Permission logic: decorators, role checks, owner IDs hardcoded anywhere.
- Environment variables read (names of secrets especially).
- Persistent data: files/databases, where they live, their schema.
- Third-party packages in your current requirements file.

## 3. Port every prefix command to a slash command

Pour the old command over using this mapping:

| Prefix-era construct                                  | Template equivalent                                                                                     |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `@bot.command()` / `@commands.command(..., help=...)` | `@app_commands.command(name=..., description=...)` — the description feeds the auto `/help`             |
| `ctx: commands.Context` parameter                     | `interaction: discord.Interaction`                                                                       |
| `ctx.send(...)` (first reply)                         | `await interaction.response.send_message(...)`                                                           |
| slow work (> ~3 s) or a second reply                  | `await interaction.response.defer(thinking=True)` then `await interaction.followup.send(...)`            |
| `ctx.author`                                          | `interaction.user` (a `discord.Member` inside a guild)                                                   |
| converters / mention parsing (`MemberConverter`, …)   | plain type hints: `member: discord.Member`, `role: discord.Role`, `channel: discord.abc.GuildChannel`, …  |
| optional args (`amount: int = 1`, `*, reason: str`… ) | same as normal parameters — options with defaults become optional                                        |
| `aliases=[...]`                                       | none — one canonical name; Discord's UI autocompletes                                                    |
| `hidden=True`                                         | n/a — ops belong in an owner prefix cog, which never appears in `/help` anyway                            |
| `@commands.has_permissions(...)`                      | `@has_permissions(...)`, `@is_mod()`, `@is_admin()`, `@is_bot_owner()` from `src/utils/checks.py`         |
| `@commands.cooldown(...)`                             | `@app_commands.checks.cooldown(rate, per)`                                                              |
| usage-error handling for missing arguments            | not needed — Discord's UI enforces required slash parameters                                             |
| `cog_command_error` catching bad usage                | rely on `BotTree`; for command-specific handling add `@cmd.error` (see below)                             |

- **Choices / autocomplete**: restrict a parameter with
  `Literal["a", "b"]` typing hints, `@app_commands.choices(...)`, or
  `app_commands.Choice`-producing autocomplete.
- **First reply within ~3 seconds.** Anything slower must `defer()` first.
- **Decorator order**: `@app_commands.command(...)` on top, permission checks
  above the function body, below the command decorator.

## 4. Rehome cogs into `cogs/`

1. Copy each feature module into `cogs/` (or create a folder for it).
2. Ensure the class keeps deriving from `commands.Cog` and takes `bot`
   in `__init__`.
3. Add the extension contract the auto-loader requires:

   ```python
   async def setup(bot: commands.Bot):
       await bot.add_cog(MyCog(bot))
   ```

4. Delete your old loading code — no `bot.load_extension` calls, no cog lists;
   `cogs/__init__.py` discovers everything.

**File vs. folder**: a cog that needs helper modules becomes a folder
(`cogs/<name>/__init__.py` holds `setup()`; internal relative imports such as
`from .helpers import x` are fine). A single-file feature stays a `cogs/<name>.py`.

**Rules bundled with the loader:**

- Names must be valid module names; files/folders starting with `_` are
  skipped, as is `cogs/template.py`. If you copy `template.py` as a starting
  point, rename it immediately.
- A folder without `__init__.py` is silently skipped.
- A cog that raises during load is logged and skipped: if a command doesn't
  show up, check `logs/bot.log`.
- Imports are absolute and run from the repo root: `from src.utils.x import
  ...`. Cross-package relative imports (`from ..src...`) do not work.

**If your old bot subclasses `commands.Bot` in its own file**: keep that
subclassing inside `main.py`. Move feature logic out of your old `Bot` class
into cogs; `main.py` in this template already defines the `Bot` subclass and
you normally won't touch it.

## 5. Adopt the built-in infrastructure instead of your own

- **Permissions**: delete custom decorators/role checks and use
  `src/utils/checks.py`. Checks raise typed `CheckFailure`s; `BotTree`
  (`src/utils/tree.py`) replies ephemerally, so per-command permission error
  messages are already handled. Unhandled check failures still get a generic
  permission message.
- **Error handling**: no global error handler needed. For a special case,
  attach a local one: `@my_command.error` on the slash command.
- **Logging**: use `logging.getLogger(__name__)` in cogs. `setup_logging` is
  called once in `main.py` (console + rotating `logs/bot.log`); do not add a
  second logging setup.
- **Constants**: replace scattered paths/flags with entries in
  `src/utils/constants.py` (it already holds `PROJECT_ROOT`, `COGS_PATH`,
  `IGNORED_COGS`) and import them.
- **Help / pagination**: drop a custom `/help`; `cogs/help.py` builds it from
  command names + descriptions. Reuse `src/utils/pagination.py::Paginator` for
  any multi-page embed you migrate.

## 6. Owner-only operational commands

Tooling like eval, database maintenance, or shutdown does not become a slash
command — fold it into `cogs/owner.py` alongside `!sync`, `!cogs`,
`!load`/`!unload`/`!reload`, `!shutdown`, guarded by
`is_bot_owner_prefix()` (plain app-command checks silently do nothing on text
commands). These stay out of the auto `/help` by design.

## 7. Migrate persistent data

1. Inventory the old bot's data files (JSON, pickle, SQLite, CSV) and where
   they're read/written.
2. Consolidate under one `data/` directory at the repo root (gitignored — add
   a `data/` line to `.gitignore`).
3. Define paths in `src/utils/constants.py`:

   ```python
   DATA_DIR = PROJECT_ROOT / "data"
   ```

   …and import them in cogs. Update `constants.py` when anything repo-level
   changes — not the loader or cogs.
4. **Format guidance**: keep or convert to JSON/SQLite. Prefer moving away
   from pickle (safety: it executes data on load; and it's not diffable).
   Since the bot is async, use `uv add aiosqlite` for SQLite rather than
   blocking `sqlite3` calls in hot paths.
5. **Move the data once**: simplest is a one-off script (or manual copy) that
   copies the old files into `data/` and, if needed, rewrites them into the
   new schema; or bootstrap with `CREATE TABLE IF NOT EXISTS` / lazy file
   creation on first run.
6. **Env vars**: `.env` keeps your secrets. The template reads
   `DISCORD_TOKEN` (the only recognized token name — rename
   `BOT_TOKEN`/`DISCORD_BOT_TOKEN` etc. when you copy them over), plus
   `LOG_LEVEL`, `LOG_DIR`, and `AUTO_RELOAD`; other app settings may stay in
   `.env`, read with `os.getenv` where needed. Never commit `.env`.

## 8. Verify

```sh
uv run python -m py_compile main.py cogs/*.py src/utils/*.py
uv run main.py
```

Then in Discord:

1. `!cogs` — every ported cog should be listed as loaded (`!cogs` is an owner
   prefix command; run from an account the bot's owner).
2. `/help` — commands appear with their descriptions; a missing command
   usually means a load error, whose traceback is in `logs/bot.log`.
3. `!sync guild` — copies global commands into one server for fast testing
   (`!sync clear` undoes it). A restart also re-syncs, but renames/changes to
   commands otherwise need the sync.
4. Exercise a check-protected command as a non-privileged user: you should get
   an ephemeral permission message from `BotTree`, not silence.

## 9. Worked example

A classic prefix cog, before:

```python
import discord
from discord.ext import commands


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kick", aliases=["yeet"], help="Kick a member.")
    @commands.has_permissions(kick_members=True)
    async def kick(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"
    ):
        if member == ctx.author:
            await ctx.send("You cannot kick yourself.")
            return
        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            await ctx.send("I could not kick that member — check my role position.")
        else:
            await ctx.send(f"Kicked {member.mention} ({reason})")

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Nice try.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Usage: `{ctx.prefix}kick <member> [reason]`")


async def setup(bot):
    await bot.add_cog(Mod(bot))
```

The same feature in the template's format (`cogs/mod.py`):

```python
import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.utils.checks import has_permissions

logger = logging.getLogger(__name__)


class Mod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        if member == interaction.user:
            await interaction.response.send_message("You cannot kick yourself.", ephemeral=True)
            return
        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I could not kick that member — check my role position.", ephemeral=True
            )
            return
        logger.info("%s kicked %s (%s)", interaction.user, member, reason)
        await interaction.response.send_message(f"Kicked {member.mention} ({reason})")


async def setup(bot: commands.Bot):
    await bot.add_cog(Mod(bot))
```

What changed:

- `@app_commands.command` with a `description` → shows up in `/help`
  automatically (prefix `aliases` are gone — slash commands have one name).
- `ctx` → `interaction`; `ctx.author` → `interaction.user`; each reply is
  `interaction.response.send_message(...)` (ephemeral for the refusals).
- `commands.has_permissions` → the template's `has_permissions`, stacked below
  the command decorator. Missing permission → `MissingPermissions` → `BotTree`
  sends the ephemeral list of missing permissions.
- `cog_command_error` deleted: `BotTree` handles check failures and unexpected
  errors; missing-argument errors are impossible with slash parameters.
- One file dropped into `cogs/` — no registration change anywhere else
  (`setup()` already has the right shape in most cases).

## 10. Gotchas

- **A missing command is a load error.** The loader logs and skips; find the
  traceback in `logs/bot.log`.
- Folder cogs need `__init__.py` with `setup()`; `_`-prefixed files and
  `cogs/template.py` are ignored.
- `src/` and `main.py` are not watched by the auto-reloader — restart the bot
  after editing them.
- Reloads don't call `tree.sync()`: after changing a command's name,
  description, or parameters, restart or run `!sync` so Discord sees it.
- App-command checks don't run on prefix commands; guard `!` commands with
  `is_bot_owner_prefix()`.
- Run from the repo root; imports are `from cogs import ...` and
  `from src.utils.x import ...`.
- Don't register commands in `on_ready` or call `tree.sync()` everywhere —
  syncing happens in `setup_hook` and via `!sync`.

## 11. Final checklist

- [ ] Portal intents enabled: Message Content, Server Members, Presence.
- [ ] `.env` has `DISCORD_TOKEN` (that exact name); `.gitignore` covers `data/`.
- [ ] Every old prefix command either has a slash twin or lives in `cogs/owner.py`.
- [ ] Every cog file/folder exposes `async def setup(bot)` and a valid module name.
- [ ] No manual cog registration left in old entrypoint code.
- [ ] Permission logic replaced with `src/utils/checks.py` decorators below `@app_commands.command`.
- [ ] Constants/paths live in `src/utils/constants.py`; env secrets only in `.env`.
- [ ] Data files consolidated under `data/` with paths from `constants.py`.
- [ ] Dependencies added via `uv add` (`pyproject.toml` updated, `uv.lock` untouched).
- [ ] `uv run python -m py_compile main.py cogs/*.py src/utils/*.py` passes.
- [ ] `!cogs` lists all cogs loaded; `/help` shows all user commands.
- [ ] A non-privileged user gets ephemeral permission messages, and
      `logs/bot.log` shows no load errors.
