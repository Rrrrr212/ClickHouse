#!/usr/bin/env python3

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install it with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "community" / "config.yaml"

SHIELDS_IO_BASE = "https://img.shields.io/badge"


def load_config(config_path=None):
    path = Path(config_path) if config_path else CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_next_release(config):
    release = config.get("release", {}).get("next", {})
    if not release:
        return None
    return release


def get_scheduled_releases(config):
    return config.get("release", {}).get("schedule", [])


def parse_release_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def compute_countdown(target_date):
    now = datetime.now(timezone.utc)
    delta = target_date - now
    return delta


def format_countdown_badge(version, target_date):
    delta = compute_countdown(target_date)

    if delta.total_seconds() <= 0:
        label = f"ClickHouse%20{version}%20Released"
        message = "OUT%20NOW"
        color = "brightgreen"
    else:
        days = delta.days
        hours = delta.seconds // 3600

        if days > 0:
            time_str = f"{days}%20day{'s' if days != 1 else ''}"
        else:
            time_str = f"{hours}%20hour{'s' if hours != 1 else ''}"

        label = f"Next%20Release%20{version}"
        message = f"in%20{time_str}"
        color = "blue" if days > 7 else "yellow" if days > 1 else "orange"

    badge_url = f"{SHIELDS_IO_BASE}/{label}-{message}-{color}?style=for-the-badge"
    return badge_url


def format_countdown_markdown(version, target_date, event_url=None):
    delta = compute_countdown(target_date)
    badge_url = format_countdown_badge(version, target_date)

    if event_url:
        markdown = f"[![Release Countdown]({badge_url})]({event_url})"
    else:
        markdown = f"![Release Countdown]({badge_url})"

    return markdown


def format_countdown_text(version, target_date):
    delta = compute_countdown(target_date)

    if delta.total_seconds() <= 0:
        return f"ClickHouse {version} has been released!"

    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    if days > 0:
        return f"ClickHouse {version} releases in {days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''}"
    elif hours > 0:
        return f"ClickHouse {version} releases in {hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return f"ClickHouse {version} releases in {minutes} minute{'s' if minutes != 1 else ''}"


def format_schedule_table(schedule):
    if not schedule:
        return ""

    lines = ["| Version | Planned Date |", "|---------|-------------|"]
    now = datetime.now(timezone.utc)

    for entry in schedule:
        version = entry.get("version", "")
        date_str = entry.get("date", "")
        try:
            date = parse_release_date(date_str)
            delta = compute_countdown(date)
            if delta.total_seconds() <= 0:
                status = "✅ Released"
            else:
                status = f"{delta.days} days away"
        except ValueError:
            status = "TBD"
        lines.append(f"| {version} | {date_str} | {status} |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate release countdown badge from community/config.yaml")
    parser.add_argument("--config", default=None, help="Path to config.yaml (default: community/config.yaml)")
    parser.add_argument(
        "--format",
        choices=["markdown", "badge-url", "text", "schedule"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument("--date", default=None, help="Override release date (YYYY-MM-DD)")
    parser.add_argument("--version", default=None, help="Override release version")
    parser.add_argument("--url", default=None, help="Override event URL")
    args = parser.parse_args()

    config = load_config(args.config)
    release = get_next_release(config)

    if not release and not args.date:
        print("Error: No next release found in config.yaml and no --date override provided.", file=sys.stderr)
        sys.exit(1)

    version = args.version or (release.get("version", "") if release else "")
    date_str = args.date or (release.get("date", "") if release else "")
    event_url = args.url or (release.get("event_url", "") if release else "")

    if not date_str:
        print("Error: No release date available.", file=sys.stderr)
        sys.exit(1)

    try:
        target_date = parse_release_date(date_str)
    except ValueError:
        print(f"Error: Invalid date format '{date_str}'. Expected YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    if args.format == "markdown":
        print(format_countdown_markdown(version, target_date, event_url or None))
    elif args.format == "badge-url":
        print(format_countdown_badge(version, target_date))
    elif args.format == "text":
        print(format_countdown_text(version, target_date))
    elif args.format == "schedule":
        schedule = get_scheduled_releases(config)
        output = format_schedule_table(schedule)
        if output:
            print(output)
        else:
            print("No scheduled releases found in config.yaml.")


if __name__ == "__main__":
    main()
