# Template Reference

A feature tour and API reference for this template: what it ships, how the
pieces behave, and every public helper in `src/utils/`.

For the architecture and runtime flows, see
[`ARCHITECTURE.md`](../ARCHITECTURE.md). For porting an existing bot, see
[`MIGRATION.md`](../MIGRATION.md). For day-to-day operating rules, see
[`AGENTS.md`](../AGENTS.md).

## Contents

- [Quick start](#quick-start)
- [What's included](#whats-included)
- [Project layout](#project-layout)
- [Configuration](#configuration)
- [Features](#features)
  - [Startup and bootstrap](#startup-and-bootstrap)
  - [Cog discovery](#cog-discovery)
  - [Slash commands and /help](#slash-commands-and-help)
  - [Owner commands](#owner-commands)
  - [Permissions](#permissions)
  - [Cooldowns](#cooldowns)
  - [Error handling](#error-handling)
  - [Embeds](#embeds)
  - [Pagination](#pagination)
  - [Hot reload](#hot-reload)
  - [Logging](#logging)
  - [Persistence](#persistence)
- [`src/utils` API](#srcutils-api)
  - [constants](#constants)
  - [checks](#checks)
  - [embeds](#embeds-api)
  - [pagination](#pagination-api)
  - [logging](#logging-api)
  - [reloader](#reloader-api)
  - [tree](#tree-api)
- [`cogs` reference](#cogs-reference)
- [Recipes](#recipes)
- [Troubleshooting](#troubleshooting)

## Quick start

```sh
cp .env.example .env    # set DISCORD_TOKEN
uv sync                 # install dependencies
uv run main.py          # start the bot
```

In the Discord Developer Portal, enable the privileged intents **Message
Content**, **Server Members**, and **Presence** — the bot requests all
intents, and login fails without them.

User-facing commands are slash commands (`/help`, `/ping`, ...). The `!` prefix
is reserved for owner operations (`!sync`, `!shutdown`, ...).

## What's included

| Feature | Where | What it does |
| --- | --- | --- |
| Auto cog discovery | `cogs/__init__.py` | Loads every valid cog in `cogs/` on startup. |
| Auto `/help` | `cogs/help.py`, `src/utils/embeds.py` | Builds help pages from command names and descriptions. |
| Owner ops | `cogs/owner.py` | `!sync`, `!cogs`, `!load`, `!unload`, `!reload`, `!shutdown`. |
| Permissions | `src/utils/checks.py` | `is_bot_owner()`, `is_admin()`, `is_mod()`, `has_permissions(...)`. |
| Cooldowns | `src/utils/checks.py` | `cooldown(rate, per, key=...)` with friendly replies. |
| Error handling | `src/utils/tree.py` | Ephemeral replies for check/cooldown failures, logged tracebacks otherwise. |
| Status embeds | `src/utils/embeds.py` | `success()`, `error()`, `warning()`, `info()`. |
| Pagination | `src/utils/pagination.py` | Author-locked Previous/Next embed paginator. |
| Hot reload | `src/utils/reloader.py` | Reloads changed cogs without a restart. |
| Logging | `src/utils/logging.py` | Console plus rotating `logs/bot.log`. |
| Data path | `src/utils/constants.py` | Gitignored `data/` for runtime state. |
| Snippet | `cogs/template.py` | Copy-paste cog skeleton, ignored by the loader. |

## Project layout

```
main.py                     # only entrypoint
cogs/                       # features, auto-discovered
  __init__.py               # load_cogs(bot)
  help.py                   # /help
  ping.py                   # /ping
  owner.py                  # ! owner commands
  template.py               # snippet, ignored by the loader
src/
  utils/
    constants.py            # PROJECT_ROOT, COGS_PATH, DATA_PATH, IGNORED_COGS
    logging.py              # setup_logging()
    tree.py                 # BotTree
    checks.py               # permission + cooldown decorators
    embeds.py               # /help + status embeds
    pagination.py           # Paginator
    reloader.py             # CogReloader
docs/
  template.md               # this file
```

Run everything from the repo root. `cogs` and `src` are top-level packages, so
imports are absolute: `from cogs import ...`, `from src.utils.x import ...`.
Cross-package relative imports do not work.

## Configuration

| Env var | Default | Meaning |
| --- | --- | --- |
| `DISCORD_TOKEN` | — | Required. The bot refuses to start if unset. |
| `LOG_LEVEL` | `INFO` | Root logger level. Invalid values fall back to `INFO`. |
| `LOG_DIR` | `logs` | Directory for the rotating `bot.log`. Created on startup. |
| `AUTO_RELOAD` | `true` | Enables the `cogs/` watcher. Truthy: `1`, `true`, `yes`, `on`. |

There are no other environment variables. Add new ones to `.env.example`, read
them with `os.getenv`, and document them in `ARCHITECTURE.md` and `AGENTS.md`.

## Features

### Startup and bootstrap

`main.py` is the only entrypoint and is never imported by other modules.
On startup it:

1. Loads `.env` with `python-dotenv`.
2. Calls `setup_logging()` once on the root logger.
3. Reads `DISCORD_TOKEN` and raises `ValueError` if it is missing.
4. Creates `Bot`, a `commands.Bot` subclass with prefix `"!"`, all intents,
   and `tree_cls=BotTree`.
5. `run(..., log_handler=None)` so discord.py does not add duplicate handlers.

`Bot.setup_hook()` then:

1. Calls `load_cogs(bot)` — every valid cog is loaded.
2. Runs a **global** `tree.sync()` — slash commands exist without manual
   syncing.
3. Starts `CogReloader(bot)`.

### Cog discovery

`cogs/__init__.py::load_cogs()` scans `cogs/` in sorted order:

- A cog is either `cogs/<name>.py` or a `cogs/<name>/` folder containing
  `__init__.py`.
- Both must expose `async def setup(bot: commands.Bot)`.
- The extension name is `cogs.<stem>` for files and `cogs.<folder>` for
  folders, so names must be valid module names (letters, digits, underscores;
  no spaces or hyphens).
- Skipped entries: `IGNORED_COGS` (`__init__.py`, `template.py`) and names
  starting with `_`.
- A cog that raises during load is logged and **skipped**, not fatal. A missing
  command almost always means a load error — check `logs/bot.log`.

Minimal file cog:

```python
# cogs/hello.py
import discord
from discord import app_commands
from discord.ext import commands


class Hello(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Say hello.")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Hello(bot))
```

Folder cog:

```
cogs/tags/
  __init__.py     # setup(bot) and the cog
  store.py        # helper module; use relative imports inside the folder
```

For a folder cog, `setup()` lives in `__init__.py` and the extension name is
`cogs.tags`. Editing any file inside the folder hot-reloads the whole package.

### Slash commands and /help

- All user-facing commands are `@app_commands.command`.
- `name` and `description` feed `/help`; commands without a description show
  "No description provided."
- `/help` reads the live command tree, sorts commands by name, and puts up to
  8 per page. One page is sent as a plain embed; multiple pages get the
  [`Paginator`](#pagination-api).
- Command groups are flattened into their leaf commands. A group with no
  leaves appears as a single entry.
- Context-menu commands are not included in `/help`.
- Reloads update the in-memory tree but do **not** call `tree.sync()`. Restart
  after changing a command name, description, or parameters, or run the
  owner-only `!sync`.

### Owner commands

All `!` commands live in `cogs/owner.py`, are bot-owner only, and never appear
in `/help`.

| Command | Effect |
| --- | --- |
| `!sync` or `!sync global` | Global sync of the slash command tree. |
| `!sync guild` | Copy global commands into the current server and sync them there (fast testing). |
| `!sync clear` | Empty the current server's command copy and sync. |
| `!cogs` | List every cog on disk and whether it is loaded. |
| `!load <name>` | Load a cog that is on disk but not loaded. |
| `!unload <name>` | Unload a loaded cog. Refuses to unload `cogs.owner`. |
| `!reload <name>` | Reload a loaded cog. |
| `!shutdown` | Send a goodbye message and close the bot. |

Unknown options and extension failures are reported in the channel; unhandled
prefix errors are logged and answered by `cog_command_error`. Prefix commands
do not get `BotTree` error handling, so a new prefix command must handle its
own errors.

### Permissions

Decorators from `src/utils/checks.py` sit **below** `@app_commands.command` and
closest to the function:

```python
from src.utils.checks import cooldown, is_mod

@app_commands.command(name="purge", description="Delete messages.")
@is_mod()
@cooldown(1, 10)
async def purge(self, interaction: discord.Interaction, amount: int):
    ...
```

| Decorator | Passes when |
| --- | --- |
| `is_bot_owner()` | The invoker is the bot owner or an application-team member. |
| `is_admin()` | The member has `Administrator`. |
| `is_mod()` | The member is an administrator or has any moderator permission. |
| `has_permissions(**perms)` | The member has every permission passed as `True`. |
| `cooldown(...)` | The invoker is inside their rate limit (see below). |

`is_mod()` accepts any of: `manage_messages`, `kick_members`, `ban_members`,
`moderate_members`, `manage_threads`, `manage_channels` (listed in
`MODERATOR_PERMISSIONS`).

Failures raise custom `app_commands.CheckFailure` subclasses and `BotTree`
answers ephemerally:

| Exception | Message |
| --- | --- |
| `OwnerOnly` | "This command can only be used by the bot owner." |
| `AdminOnly` | "This command requires the `Administrator` permission." |
| `ModOnly` | "This command requires moderator permissions." / DM variant |
| `MissingPermissions(permissions)` | "You are missing the following permissions: ..." |

Permission checks read `interaction.user.guild_permissions`; in DMs there is no
member, so they fail closed.

`is_bot_owner_prefix()` is the text-command equivalent of `is_bot_owner()`. It
returns a `commands.check` instead of an `app_commands.check`, because
application-command checks do not run on prefix commands.

### Cooldowns

```python
from src.utils.checks import cooldown

@cooldown(3, 60)                              # 3 uses per 60 s, per user (default)
@cooldown(3, 60, key=lambda i: i.guild_id)    # per server
@cooldown(1, 5, key=lambda _: None)           # one global bucket
```

- `rate` is the number of uses, `per` is the window in seconds.
- The default bucket is per user (`interaction.user.id`).
- `key` receives the interaction and returns any hashable bucket key; async
  key functions are supported. The wrapper treats `key=None` as "use the
  default per-user bucket" — pass `lambda _: None` for one global bucket.
- When the limit is hit, `BotTree` replies ephemerally with
  "Slow down — try again in N.Ns."

### Error handling

`BotTree` (`src/utils/tree.py`, wired with `tree_cls=BotTree`) is the single
error handler for application commands. In order:

1. If the interaction was already answered, do nothing.
2. `app_commands.CommandOnCooldown` → ephemeral message with `retry_after`.
3. `checks.py` failures (`OwnerOnly`, `AdminOnly`, `ModOnly`,
   `MissingPermissions`) → ephemeral `str(error)`.
4. Any other `CheckFailure` → generic ephemeral permission message.
5. Anything else → log the traceback and reply "Something went wrong while
   running this command." ephemerally.

If a command deferred and then raised, the interaction counts as answered, so
`BotTree` does not send a second message. Commands that defer must send their
own error follow-up.

`BotTree` covers application-command interactions (slash commands and context
menus) only. Component/modal callbacks and prefix commands need their own
handling; `cogs/owner.py` handles prefix errors in `cog_command_error`.

### Embeds

`src/utils/embeds.py` provides four status embeds plus the `/help` builder:

```python
from src.utils.embeds import error, info, success, warning

await interaction.response.send_message(embed=success("Settings saved."))
await interaction.response.send_message(
    embed=error("You need **Manage Messages**.", title="Permission denied"),
    ephemeral=True,
)
```

| Helper | Color | Default title |
| --- | --- | --- |
| `success(description)` | green | `Success` |
| `error(description)` | red | `Error` |
| `warning(description)` | orange | `Warning` |
| `info(description)` | blurple | `Info` |

Each helper takes `description` positionally and an optional keyword-only
`title`. For `error()`, `title` is the type-of-error label (for example
`"Permission denied"`, `"Not found"`, `"Invalid input"`).

### Pagination

Use `Paginator` when a reply needs more than one embed page:

```python
from src.utils.pagination import Paginator

await interaction.response.send_message(
    embed=pages[0],
    view=Paginator(pages, author_id=interaction.user.id),
)
```

- Buttons: Previous, page counter, Next.
- Only `author_id` may navigate; anyone else gets an ephemeral notice.
- The page counter is a disabled display button.
- Timeout is 180 seconds by default (`timeout=` to override).
- The view does not delete the message when it expires.

See `cogs/help.py` for the reference usage.

### Hot reload

`CogReloader` watches `cogs/` with `watchfiles`:

- Added and modified `.py` files are loaded or reloaded.
- A top-level file maps to `cogs.<stem>`; a file inside a folder maps to
  `cogs.<folder>`, reloading the whole package.
- Skipped: `__pycache__`, `_`-prefixed names, and `IGNORED_COGS`. Deletions are
  not handled.
- Reloads update the in-memory command tree but do **not** sync it. Restart or
  run `!sync` after changing a command name, description, or parameters.
- `src/` and `main.py` are not watched; restart after editing them.
- Set `AUTO_RELOAD=false` to disable the watcher (recommended in production).

### Logging

`src/utils/logging.py::setup_logging()` is called exactly once, in `main.py`.
Do not call it again. It configures:

- Console output through `discord.utils.setup_logging(..., root=True)`.
- A rotating file handler at `<LOG_DIR>/bot.log`: 5 MB × 5 files.
- `LOG_LEVEL` on the root logger; invalid levels fall back to `INFO`.
- `<LOG_DIR>` is created if missing.

In your own modules, just do:

```python
import logging

logger = logging.getLogger(__name__)
```

Log output is gitignored (`logs/`, `*.log`).

### Persistence

The template ships no database or file storage. Runtime state belongs under
`DATA_PATH`, which points at the gitignored `data/` directory:

```python
from src.utils.constants import DATA_PATH

DATA_PATH.mkdir(parents=True, exist_ok=True)
db_path = DATA_PATH / "bot.db"
```

`DATA_PATH` is not created for you; create it when first writing. Keep every
database, cache, and upload under it so one directory covers all state.

## `src/utils` API

Everything below is imported absolutely, for example
`from src.utils.checks import is_mod`. `src/utils/__init__.py` is empty on
purpose; import from the module you need.

### constants

```python
from src.utils.constants import COGS_PATH, DATA_PATH, IGNORED_COGS, PROJECT_ROOT
```

| Name | Type | Value / meaning |
| --- | --- | --- |
| `PROJECT_ROOT` | `pathlib.Path` | Repo root (`Path(__file__).resolve().parents[2]`). |
| `COGS_PATH` | `pathlib.Path` | `PROJECT_ROOT / "cogs"`. |
| `DATA_PATH` | `pathlib.Path` | `PROJECT_ROOT / "data"`; gitignored runtime state. |
| `IGNORED_COGS` | `set[str]` | `{"__init__.py", "template.py"}`; skipped by the loader and reloader. |

Add new shared paths and flags here rather than in `cogs/__init__.py`.

### checks

```python
from src.utils.checks import (
    AdminOnly,
    CooldownKey,
    MissingPermissions,
    ModOnly,
    MODERATOR_PERMISSIONS,
    OwnerOnly,
    cooldown,
    has_permissions,
    is_admin,
    is_bot_owner,
    is_bot_owner_prefix,
    is_mod,
)
```

#### Decorators

All application-command decorators return an `app_commands.check` and stack
with other decorators. Put them below `@app_commands.command(...)`.

| Function | Signature | Raises on failure |
| --- | --- | --- |
| `is_bot_owner` | `is_bot_owner()` | `OwnerOnly` |
| `is_admin` | `is_admin()` | `AdminOnly` |
| `is_mod` | `is_mod()` | `ModOnly` |
| `has_permissions` | `has_permissions(**perms: bool)` | `MissingPermissions` |
| `cooldown` | `cooldown(rate, per, *, key=None)` | `app_commands.CommandOnCooldown` |
| `is_bot_owner_prefix` | `is_bot_owner_prefix()` | `OwnerOnly` (for `!` text commands) |

`has_permissions` only requires the permissions passed as `True`; entries set
to `False` are ignored:

```python
@has_permissions(manage_guild=True, manage_roles=True)
```

`cooldown(rate: int, per: float, *, key: CooldownKey | None = None)` — see
[Cooldowns](#cooldowns). `CooldownKey` is
`Callable[[discord.Interaction], Hashable | Awaitable[Hashable]]`.

#### Exceptions

| Exception | Constructor | Public attributes |
| --- | --- | --- |
| `OwnerOnly(message)` | `app_commands.CheckFailure` subclass | — |
| `AdminOnly(message)` | `app_commands.CheckFailure` subclass | — |
| `ModOnly(message)` | `app_commands.CheckFailure` subclass | — |
| `MissingPermissions(permissions)` | builds "You are missing..." | `.permissions: set[str]` |

`BotTree` matches the four types in `CHECK_FAILURES` and replies with their
message. If you add a new check-failure type, add it to `CHECK_FAILURES` in
`src/utils/tree.py` for a tailored reply; otherwise it gets the generic
permission message.

`MODERATOR_PERMISSIONS` is the tuple used by `is_mod()`:
`manage_messages`, `kick_members`, `ban_members`, `moderate_members`,
`manage_threads`, `manage_channels`.

### embeds API

```python
from src.utils.embeds import (
    COMMANDS_PER_PAGE,
    ERROR_COLOR,
    HELP_COLOR,
    INFO_COLOR,
    SUCCESS_COLOR,
    WARNING_COLOR,
    build_help_pages,
    collect_command_entries,
    error,
    info,
    success,
    warning,
)
```

#### Status embeds

| Function | Signature |
| --- | --- |
| `success` | `success(description: str, *, title: str = "Success") -> discord.Embed` |
| `error` | `error(description: str, *, title: str = "Error") -> discord.Embed` |
| `warning` | `warning(description: str, *, title: str = "Warning") -> discord.Embed` |
| `info` | `info(description: str, *, title: str = "Info") -> discord.Embed` |

Colors: `SUCCESS_COLOR` (green), `ERROR_COLOR` (red), `WARNING_COLOR`
(orange), `INFO_COLOR` (blurple), `HELP_COLOR` (blurple).

#### Help builders

`collect_command_entries(commands)` flattens an iterable of application
commands into sorted `(qualified_name, description)` pairs:

- Groups are flattened into leaf commands; a childless group is kept as one
  entry.
- Context menus are skipped.
- An empty or `"…"` / `"..."` description becomes "No description provided."
- Sorting is case-insensitive by name.

`build_help_pages(commands, *, bot_name: str, per_page: int = COMMANDS_PER_PAGE)`
returns a list of `discord.Embed` pages. `COMMANDS_PER_PAGE` is `8`. If there
are no entries, it returns one page containing a placeholder entry.

```python
from src.utils.embeds import build_help_pages
from src.utils.pagination import Paginator

pages = build_help_pages(self.bot.tree.get_commands(), bot_name="MyBot")
```

### pagination API

```python
from src.utils.pagination import Paginator
```

```python
Paginator(
    pages: list[discord.Embed],
    *,
    author_id: int,
    timeout: float = 180.0,
)
```

| Member | Description |
| --- | --- |
| `pages` | Embed list to page through. |
| `author_id` | Only this user may use the buttons. |
| `index` | Current page index (0-based). |
| `timeout` | Seconds before the view stops responding. |
| `interaction_check(interaction)` | Author lock; other users get an ephemeral notice. |

Buttons: `previous_button`, `page_button` (disabled counter), `next_button`.
The view is not removed automatically when it times out.

### logging API

```python
from src.utils.logging import setup_logging

setup_logging()
```

| Name | Description |
| --- | --- |
| `setup_logging()` | Configure console + rotating file logging on the root logger. Call once, from `main.py`. |
| `LOG_FORMAT` | `%(asctime)s %(levelname)-8s %(name)s: %(message)s` |
| `LOG_DATE_FORMAT` | `%Y-%m-%d %H:%M:%S` |

The file handler writes `<LOG_DIR>/bot.log`, rotating at 5 MB with 5 backups.
Levels come from `LOG_LEVEL`; the directory comes from `LOG_DIR` (default
`logs`).

### reloader API

```python
from src.utils.reloader import CogReloader

reloader = CogReloader(bot)          # cogs_path=COGS_PATH by default
reloader.start()                     # no-op unless AUTO_RELOAD is truthy
await reloader.stop()                # cancel the watcher task
```

| Member | Description |
| --- | --- |
| `CogReloader(bot, cogs_path=COGS_PATH)` | Watcher for one directory. |
| `start()` | Create the background watch task. Idempotent. |
| `stop()` | Async; cancel the task and wait for it to finish. |
| `WATCHED_CHANGES` | Module constant: `{Change.added, Change.modified}`. |
| `_auto_reload_enabled()` | Internal env parser for `AUTO_RELOAD`. |

`start()` logs that auto-reload is disabled and returns when `AUTO_RELOAD` is
false. Watch events are debounced at 500 ms.

### tree API

```python
from src.utils.tree import BotTree
```

`BotTree` subclasses `app_commands.CommandTree` and is wired through
`tree_cls=BotTree` in `main.py`.

| Member | Description |
| --- | --- |
| `on_error(interaction, error, /)` | Single application-command error handler. |
| `CHECK_FAILURES` | Module tuple: `OwnerOnly`, `AdminOnly`, `ModOnly`, `MissingPermissions`. |

Behavior is described in [Error handling](#error-handling). Error replies are
always ephemeral; unexpected exceptions are logged with a traceback before the
generic reply.

## `cogs` reference

### `cogs/__init__.py`

```python
from cogs import load_cogs

await load_cogs(bot)
```

`load_cogs(bot)` scans `COGS_PATH`, loads each valid extension, logs failures,
and continues. It is called by `Bot.setup_hook()`; you should not need to call
it yourself.

### `cogs/help.py`

`/help` — lists every application command with its description, paging with
`Paginator` when needed. Reads the live tree, so no help text to maintain.

### `cogs/ping.py`

`/ping` — replies with `Pong!` and the gateway latency in milliseconds.

### `cogs/owner.py`

Owner-only prefix commands described in [Owner commands](#owner-commands).
The `Owner` cog also exposes `cog_command_error`, which handles permission
failures and logs unexpected prefix-command errors.

### `cogs/template.py`

A copy-paste snippet, not a real cog:

- It is listed in `IGNORED_COGS`, so the loader skips it.
- It has no `setup()`, so it cannot be loaded as-is.
- To use it: copy it, add `description=` to the command, add the usual
  `async def setup(bot)`, and rename the file to a valid module name.

## Recipes

### Add a slash command

```python
# cogs/echo.py
import discord
from discord import app_commands
from discord.ext import commands

from src.utils.checks import cooldown


class Echo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="echo", description="Repeat a message.")
    @cooldown(3, 30)
    async def echo(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Echo(bot))
```

Restart the bot (or run `!sync`) after adding it so Discord sees the command.

### Add a folder cog

```
cogs/tags/
  __init__.py
  store.py
```

`__init__.py` defines `Tags(commands.Cog)` and `setup(bot)`; `store.py` can
import sibling modules relatively (`from .store import ...`). Editing either
file reloads `cogs.tags`.

### Paginate a long response

```python
import discord

from src.utils.pagination import Paginator


def build_pages(entries: list[str]) -> list[discord.Embed]:
    return [
        discord.Embed(title="Results", description="\n".join(chunk))
        for chunk in (entries[i : i + 10] for i in range(0, len(entries), 10))
    ]


pages = build_pages(entries)
if len(pages) == 1:
    await interaction.response.send_message(embed=pages[0])
else:
    await interaction.response.send_message(
        embed=pages[0],
        view=Paginator(pages, author_id=interaction.user.id),
    )
```

### Store state under `DATA_PATH`

```python
import json

from src.utils.constants import DATA_PATH


def save_settings(guild_id: int, settings: dict) -> None:
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    path = DATA_PATH / f"guild-{guild_id}.json"
    path.write_text(json.dumps(settings), encoding="utf-8")
```

For SQLite, use `DATA_PATH / "bot.db"` as the database path and create the
directory before opening it.

### Add an owner command

Add a `@commands.command` in `cogs/owner.py` guarded with
`@is_bot_owner_prefix()`. `Owner.cog_command_error` handles `OwnerOnly` and
other prefix-command failures. Remember that prefix commands never appear in
`/help`.

### Add a new permission tier

1. Define a `CheckFailure` subclass in `src/utils/checks.py`.
2. Write a decorator that raises it, returning `app_commands.check(predicate)`.
3. Add the exception to `CHECK_FAILURES` in `src/utils/tree.py` so its message
   is shown verbatim.
4. Document it in `ARCHITECTURE.md`, `MIGRATION.md`, and this file.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| A slash command is missing | Its cog failed to load, or the tree was not synced | Check `logs/bot.log`, run `!cogs`, then `!sync`. |
| A renamed command still shows the old name | Command metadata changed without a sync | Restart or run `!sync`. |
| A new/renamed command works locally but not in another server | Guild vs. global sync | Use `!sync global`, or `!sync guild` for testing. |
| Login fails with `PrivilegedIntentsRequired` | Privileged intents are off in the portal | Enable Message Content, Server Members, Presence. |
| Edits to `src/` do nothing | Only `cogs/` is watched | Restart the bot. |
| Edits to a cog's command name do nothing | Reload does not re-sync | Restart or `!sync`. |
| A user sees "You do not have permission" for a cooldown | A local error handler catches `CheckFailure` before checking `CommandOnCooldown` | Handle `CommandOnCooldown` first, or let `BotTree` handle it. |
| Permission checks fail in DMs | There is no guild member in DMs | Guard the command with `is_mod()`/`is_admin()` and document DM behavior. |
| `data/` or `logs/` is missing | Both are gitignored runtime directories | `setup_logging()` creates `LOG_DIR`; create `DATA_PATH` with `DATA_PATH.mkdir(...)`. |

## Verification

```sh
uv run python -m py_compile main.py cogs/*.py src/utils/*.py
uv run main.py
```

Then, in Discord:

1. `!cogs` — every cog should be listed as loaded.
2. `/help` — every slash command should appear with a description.
3. `/ping` — should return latency.
4. `!sync` — should re-sync the global tree.

If a command is missing, read `logs/bot.log` first: that is where a cog skipped
during load reports its traceback.
