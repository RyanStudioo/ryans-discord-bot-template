# AGENTS.md

Discord bot template. Python >=3.13, discord.py 2.7.1, uv-managed. User commands are slash commands only; `!` prefix commands are reserved for owner ops (`cogs/owner.py`).

## Documentation

Three docs describe this repo and must stay in sync with the code:

- `ARCHITECTURE.md` — the architecture: components, contracts, runtime flows.
- `MIGRATION.md` — porting an existing discord.py bot into this format.
- `AGENTS.md` (this file) — operational rules and commands.

Any change to the architecture — layout, entrypoint, cog loading rules,
`src/utils` contracts, constants, env vars, command or permission philosophy —
or anything major for the migration story must be reflected in **both**
`ARCHITECTURE.md` and `MIGRATION.md` in the same change set. Update this file
too whenever a working rule changes. A code change without the matching doc
updates is incomplete.

## Setup / commands

- `cp .env.example .env`, then set `DISCORD_TOKEN`.
- `uv sync` — install dependencies.
- `uv run main.py` — start the bot.
- `uv add <package>` — add a dependency (updates `pyproject.toml` and `uv.lock`; never hand-edit the lock).
- No tests, linter, typechecker, or CI are configured. Minimum check: `uv run python -m py_compile main.py cogs/*.py src/utils/*.py`.

## Runtime

- `main.py` is the only entrypoint. `Bot.setup_hook()` loads cogs, runs a global `tree.sync()`, then starts `CogReloader`.
- Logging is configured once in `src/utils/logging.py`; `client.run(..., log_handler=None)` prevents discord.py from adding duplicate handlers. Do not add another `setup_logging` call.
- Env vars: `DISCORD_TOKEN` is the only token name read; also `LOG_LEVEL`, `LOG_DIR` (default `logs`), and `AUTO_RELOAD` (default true). Output goes to console and rotating `logs/bot.log` (gitignored).
- `Intents.all()` is used, so login fails unless Message Content, Server Members, and Presence are enabled in the Discord Developer Portal.

## Cogs

- `cogs/__init__.py` auto-loads every cog except `IGNORED_COGS` and `_`-prefixed names. A cog is either a `cogs/*.py` file or a `cogs/<name>/` folder containing `__init__.py`; both must expose `async def setup(bot)` (for folders, define it in `__init__.py`). The extension name is `cogs.<stem>` or `cogs.<folder>`, so names must be valid module names.
- A cog that raises during load is logged and skipped, so a missing command usually means a load error. Check `logs/bot.log`.
- `src/utils/constants.py` holds `COGS_PATH`, `IGNORED_COGS`, and `PROJECT_ROOT = parents[2]`. Update these there, not in `cogs/__init__.py`.
- `cogs/template.py` is intentionally ignored, is only a snippet, and has no `setup()`. Copy it, add `setup()`, then rename it.
- Prefix commands (`!`) are owner-only ops in `cogs/owner.py`: `!sync [global|guild|clear]`, `!cogs`, `!load`, `!unload`, `!reload`, `!shutdown`. They never appear in auto `/help`. Everything user-facing is a slash command: add `@app_commands.command(name=..., description=...)`; names and descriptions feed the auto `/help` (`cogs/help.py`). Commands without a description show "No description provided."

## Permission checks

- `src/utils/checks.py` provides `is_bot_owner()`, `is_admin()`, `is_mod()`, `has_permissions(...)`, and `is_bot_owner_prefix()` (the bot-owner check for `!` prefix commands — app-command checks silently do nothing on text commands).
- Put checks below `@app_commands.command(...)`, closest to the function:

```python
@app_commands.command(name="purge", description="Delete messages.")
@is_mod()
async def purge(interaction: discord.Interaction, amount: int): ...
```

- Checks raise custom `app_commands.CheckFailure` subclasses. `BotTree` (`src/utils/tree.py`, wired via `tree_cls=BotTree`) replies ephemerally; unhandled check failures fall back to a generic permission message.

## Auto-reload

- `watchfiles` watches only `cogs/`. Modified and new `.py` files are reloaded/loaded automatically; changes inside a folder-based cog reload the whole `cogs.<folder>` package. `__pycache__`, `_`-prefixed names, and `IGNORED_COGS` are skipped.
- Set `AUTO_RELOAD=false` to disable it.
- Reloads update the in-memory command tree but do **not** call `tree.sync()`. Restart after changing a command name, description, or parameters so Discord picks up the change (or run the owner-only `!sync`).
- `src/` and `main.py` are not watched; restart after editing them.

## Layout

- Run from the repo root. `cogs` and `src` are top-level packages: use `from cogs import ...` and `from src.utils.x import ...`; cross-package relative imports will not work.
- `src/utils/` holds shared helpers (`checks`, `tree`, `embeds`, `pagination`, `logging`, `reloader`, `constants`); `cogs/` holds features; `main.py` wires them together.
