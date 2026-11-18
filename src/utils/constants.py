from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COGS_PATH = PROJECT_ROOT / "cogs"
DATA_PATH = PROJECT_ROOT / "data"
IGNORED_COGS = {"__init__.py", "template.py"}
