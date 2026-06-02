#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from urllib.parse import quote

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "community" / "config.yaml"


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def build_countdown_text(release_date: dt.date, today: dt.date) -> str:
    delta_days = (release_date - today).days
    if delta_days > 1:
        return f"{delta_days} days"
    if delta_days == 1:
        return "1 day"
    if delta_days == 0:
        return "today"
    if delta_days == -1:
        return "1 day ago"
    return f"{abs(delta_days)} days ago"


def build_badge_color(release_date: dt.date, today: dt.date) -> str:
    delta_days = (release_date - today).days
    if delta_days < 0:
        return "lightgrey"
    if delta_days <= 7:
        return "orange"
    if delta_days <= 21:
        return "blue"
    return "brightgreen"


def build_badge_markdown(config: dict, today: dt.date | None = None) -> str:
    release = config["next_release"]
    release_date = dt.date.fromisoformat(release["date"])
    current_day = today or dt.date.today()
    countdown_text = build_countdown_text(release_date, current_day)
    color = build_badge_color(release_date, current_day)
    label = quote("next release")
    message = quote(countdown_text)
    version = release["version"]
    target_url = release["event_url"]
    badge_url = f"https://img.shields.io/badge/{label}-{message}-{color}?style=for-the-badge&logo=clickhouse"
    return f"[![Next release {version}: {countdown_text}]({badge_url})]({target_url})"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Markdown countdown badge for the next ClickHouse release")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to community config.yaml")
    parser.add_argument("--today", type=dt.date.fromisoformat, default=None, help="Override today's date in YYYY-MM-DD format")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    print(build_badge_markdown(config, today=args.today))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
