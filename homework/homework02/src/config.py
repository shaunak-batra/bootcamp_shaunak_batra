import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")


def get_key(name: str, default=None):
    return os.getenv(name, default)
