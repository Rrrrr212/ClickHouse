#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from urllib.parse import quote

from config_loader import load_config


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "community" / "config.yaml"


def read_release(config: dict) -> dict:
    release = config.get("release")
    if not isinstance(release, dict):
        raise ValueError("Missing release configuration")
    required_keys = ("version", "date")
    missing_keys = [key for key in required_keys if not release.get(key)]
    if missing_keys:
        raise ValueError(f"Missing release keys: {', '.join(missing_keys)}")
    return release


def compute_days_until(target_date: str, today: date | None = None) -> tuple[int, date]:
    target = date.fromisoformat(target_date)
    current = today or date.today()
    return (target - current).days, target


def build_badge_message(days_until_release: int) -> str:
    if days_until_release > 0:
        return f"D-{days_until_release}"
    if days_until_release == 0:
        return "Release today"
    return f"D+{abs(days_until_release)}"


def build_badge_color(days_until_release: int) -> str:
    if days_until_release > 14:
        return "2ea44f"
    if days_until_release > 0:
        return "dfb317"
    if days_until_release == 0:
        return "8250df"
    return "9a6700"


def build_badge_markdown(config: dict, today: date | None = None) -> str:
    release = read_release(config)
    days_until_release, _ = compute_days_until(release["date"], today=today)
    version = release["version"]
    badge_style = release.get("badge_style", "for-the-badge")
    target_url = release.get("call_url", "https://clickhouse.com/company/news-events")
    alt_text = f"ClickHouse {version} release countdown"
    label = quote(f"release {version}")
    message = quote(build_badge_message(days_until_release))
    badge_url = (
        f"https://img.shields.io/badge/{label}-{message}-{build_badge_color(days_until_release)}"
        f"?style={quote(badge_style)}"
    )
    return f"[![{alt_text}]({badge_url})]({target_url})"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown countdown badge for the next ClickHouse release",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the community configuration file",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))
    print(build_badge_markdown(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
