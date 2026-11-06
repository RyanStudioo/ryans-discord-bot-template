from pathlib import Path

COGS_PATH = Path(__file__).parent
IGNORE = ["__init__.py", "template.py"]

def load_cogs(bot):
    for file in COGS_PATH.glob('*.py'):
        if file.name in IGNORE:
            continue
        bot.load_extension(f'cogs.{file.stem}')
