"""Small .env parser for local, untracked provider configuration."""

from __future__ import annotations

from pathlib import Path


def load_env_file(path: str | Path = ".env") -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _clean_value(value.strip())
    return values


def apply_env_defaults(values: dict[str, str]) -> None:
    import os

    for key, value in values.items():
        os.environ.setdefault(key, value)


def _clean_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
