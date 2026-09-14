"""Loads configuration from .env — with no external dependencies."""
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: Path = ENV_PATH) -> dict:
    variables = {}
    with open(path) as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.strip().split("=", 1)
                variables[key] = value
    return variables


ENV = load_env()
