#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def _parse_scalar(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[0] == value[-1] and value[0] in {"\"", "'"}:
        return value[1:-1]
    return value


def load_config(config_path: Path) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError(f"Invalid indentation in {config_path}: {raw_line}")

        while stack and indent <= stack[-1][0]:
            stack.pop()

        if not stack:
            raise ValueError(f"Invalid YAML structure in {config_path}")

        current = stack[-1][1]
        key, sep, value = stripped.partition(":")
        if not sep:
            raise ValueError(f"Invalid YAML line in {config_path}: {raw_line}")

        key = key.strip()
        value = value.strip()

        if value:
            current[key] = _parse_scalar(value)
            continue

        nested: dict = {}
        current[key] = nested
        stack.append((indent, nested))

    return root
