# Migrating a Bot to This Template

Everything you need in one place: how to run the template, the required file
and folder structure, the core files, and the shape your code must take.

## 1. Running it

- Python >= 3.13 installed, with [`uv`](https://docs.astral.sh/uv/).
- In the Discord Developer Portal, enable the privileged intents
  **Message Content**, **Server Members**, and **Presence** for your
  application — the bot requests all intents and login fails without them.

```sh
cp .env.example .env    # then set DISCORD_TOKEN inside
uv sync                 # install dependencies (creates .venv)
uv run main.py          # start the bot
```

Environment variables (copy `.env.example` and adjust):

| Var             | Default | Meaning                                      |
| --------------- | ------- | -------------------------------------------- |
| `DISCORD_TOKEN` | —       | Required. The bot refuses to start without it. |
| `LOG_LEVEL`     | `INFO`  | Log level for console and file output.       |
| `LOG_DIR`       | `logs`  | Where the rotating `bot.log` is written.     |
| `AUTO_RELOAD`   | `true`  | Hot-reload cogs when files in `cogs/` change. |

Extra dependencies go through `uv add <package>` (updates `pyproject.toml` and
`uv.lock`). Never `pip install` into the venv by hand.

## 2. Required structure

```
main.py                     # entrypoint — the only file that starts the bot
pyproject.toml              # Python version + dependencies (uv-managed)
.env.example                # template for .env
cogs/                       # every bot feature lives here; loaded automatically by the auto-loader
  __init__.py               # auto-loader: loads every cog (see rules below)
  owner.py                  # owner-only ops: !sync, !cogs, !load/unload/reload, !shutdown
  help.py                   # /help — built automatically from your commands
  ping.py                   # smallest working example of a cog
  template.py               # snippet to copy from; ignored by the loader
src/                        # shared infrastructure — already wired, leave as is
  utils/
    logging.py              # logging setup (console + rotating logs/bot.log) — configured once in main.py
    tree.py                 # command tree with built-in error replies for commands
    checks.py               # permission decorators (is_mod, has_permissions, ...)
    embeds.py               # builds the /help pages
    pagination.py           # button paginator used by /help
    reloader.py             # hot-reload watcher for cogs/
    constants.py            # PROJECT_ROOT, COGS_PATH, IGNORED_COGS
```

`main.py`, `cogs/__init__.py`, and everything in `src/utils/` are the core
files that make the template run. You rarely need to change them: drop your
features into `cogs/` and they get loaded, synced, hot-reloaded, and shown in
`/help` automatically.

## 3. The core files

### `main.py`

The single entrypoint. It reads `.env`, configures logging once, defines the
`Bot` subclass (`tree_cls=BotTree`, prefix `"!"`, all intents), and validates
the token. Its `setup_hook()` then does exactly three things:

1. Loads every cog found in `cogs/`.
2. Runs one global `tree.sync()` so slash commands exist.
3. Starts the `cogs/` hot-reload watcher.

### `cogs/__init__.py` (the auto-loader)

- Scans `cogs/` in sorted order.
- A cog is either a `cogs/<name>.py` file or a `cogs/<name>/` folder
  containing an `__init__.py`.
- Each must end with:

  ```python
  async def setup(bot: commands.Bot):
      await bot.add_cog(MyCog(bot))
  ```

- Skipped: `__init__.py`, `template.py`, and anything starting with `_`.
- A cog whose load raises an error is logged and skipped — so **a missing
  command almost always means a load error**. Check `logs/bot.log`.
- Names must be valid module names (letters, digits, underscores; no
  spaces or hyphens).

### `src/utils/`

Infrastructure, all pre-wired through `main.py` — use it via imports, don't
recreate it:

- `checks.py` — permission decorators for slash commands (`is_bot_owner()`,
  `is_admin()`, `is_mod()`, `has_permissions(...)`). They
  stack under `@app_commands.command` and produce the ephemeral permission
  error replies automatically.
- `tree.py` — `BotTree`, which intercepts command failures (permissions,
  errors) and answers ephemerally.
- `logging.py` — logging setup; in your own modules just use
  `logging.getLogger(__name__)`.
- `embeds.py` / `pagination.py` — build and page the auto-`/help` from command
  names and descriptions; nothing for you to maintain.
- `constants.py` — `PROJECT_ROOT` (repo root) and `COGS_PATH`; any other
  repo-level constant goes here.

## 4. What your migrated code must look like

Every feature migrates into a `cogs/` file in this shape:

```python
import discord
from discord import app_commands
from discord.ext import commands

from src.utils.checks import is_mod


class MyFeature(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="myfeature", description="Shown in /help.")
    @is_mod()                      # checks sit below @app_commands.command
    async def myfeature(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MyFeature(bot))
```

Converting from prefix commands (`!`) to slash commands:

| You had (prefix)                          | You write (here)                                    |
| ----------------------------------------- | --------------------------------------------------- |
| `@commands.command(..., help=...)`        | `@app_commands.command(name=..., description=...)`  |
| `ctx: commands.Context`                   | `interaction: discord.Interaction`                  |
| `ctx.send(...)`                           | `await interaction.response.send_message(...)`      |
| slow work / more than one reply           | `defer()` first, then `interaction.followup.send`   |
| `ctx.author`                              | `interaction.user`                                  |
| converters (`MemberConverter`, ...)       | plain type hints: `member: discord.Member`, ...     |
| `@commands.has_permissions(...)`          | decorators from `src.utils.checks` (`is_mod`, ... ) |
| use-error handlers for missing arguments  | not needed — Discord enforces required parameters   |

Rules when moving files into `cogs/`:

- Slash commands are the only user-facing commands. Owner ops (`!`) already
  exist in `cogs/owner.py` and don't appear in `/help`.
- One file per feature (or a folder with `__init__.py` when it needs helper
  modules); no manual cog registration anywhere.
- Run from the repo root and import absolutely:
  `from src.utils.checks import is_mod`. Cross-package relative imports won't work.
- After editing a command's name, description, or parameters, restart the bot
  so the sync picks it up (the hot reload alone doesn't re-sync).

## 5. Verifying

1. Run `uv run python -m py_compile main.py cogs/*.py src/utils/*.py` — this
   compiles all files, catching syntax errors.
2. Start with `uv run main.py` and open the Discord server.
3. Type `!cogs` (owner prefix command) — all your cogs should be listed.
4. Run `/help` — all your slash commands with descriptions.
5. If a command is missing, read `logs/bot.log`: this is where the cog was skipped because it failed to load.
