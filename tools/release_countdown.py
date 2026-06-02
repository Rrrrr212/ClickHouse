#!/usr/bin/env python3
"""
ClickHouse Release Countdown Automation.

Reads the next release version and date from community/config.yaml,
computes the remaining days, and generates a dynamic countdown badge
in Markdown format (compatible with shields.io).

Usage:
    python3 tools/release_countdown.py                    # print countdown info
    python3 tools/release_countdown.py --badge-only       # print only the Markdown badge
    python3 tools/release_countdown.py --markdown         # print full Markdown snippet
    python3 tools/release_countdown.py --json             # print JSON output for automation
    python3 tools/release_countdown.py -c path/to/config.yaml
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "community" / "config.yaml"


def load_yaml(path):
    try:
        import yaml
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except ImportError:
        print("Error: PyYAML is required. Install it with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)


def parse_release_date(date_str):
    return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()


def compute_countdown(release_date):
    today = datetime.date.today()
    delta = release_date - today
    return {
        "days_remaining": delta.days,
        "release_date": release_date.isoformat(),
        "today": today.isoformat(),
        "is_released": delta.days <= 0,
        "is_today": delta.days == 0,
        "is_soon": 0 < delta.days <= 7,
        "is_upcoming": delta.days > 7,
    }


def generate_shields_badge(label, message, color, style="for-the-badge"):
    label_encoded = quote(label, safe="")
    message_encoded = quote(message, safe="")
    style_encoded = quote(style, safe="")
    return (
        f"https://img.shields.io/badge/{label_encoded}-{message_encoded}-{color}"
        f"?style={style_encoded}"
    )


def generate_markdown_badge(badge_url, alt_text, link_url):
    return f"[![{alt_text}]({badge_url})]({link_url})"


def generate_countdown_badge(countdown_info, release_config):
    version = release_config.get("next_version", "?")
    days = countdown_info["days_remaining"]
    release_date_str = countdown_info["release_date"]

    release_call_url = release_config.get(
        "release_call_url_template",
        "https://clickhouse.com/company/events/v{version}-community-release-call",
    ).replace("{version}", version.replace(".", "-"))

    if countdown_info["is_released"] and not countdown_info["is_today"]:
        label = f"ClickHouse {version}"
        past = abs(days)
        message = f"Released {past}d ago"
        color = "blue"
    elif countdown_info["is_today"]:
        label = f"ClickHouse {version}"
        message = "Release today!"
        color = "brightgreen"
    elif countdown_info["is_soon"]:
        label = f"ClickHouse {version} release in"
        message = f"{days} day{'s' if days != 1 else ''}"
        color = "orange"
    else:
        label = f"ClickHouse {version} release in"
        message = f"{days} day{'s' if days != 1 else ''}"
        color = "green"

    badge_url = generate_shields_badge(label, message, color)
    alt_text = f"ClickHouse {version} release countdown: {message}"
    markdown = generate_markdown_badge(badge_url, alt_text, release_call_url)

    return {
        "badge_url": badge_url,
        "markdown": markdown,
        "label": label,
        "message": message,
        "color": color,
        "link_url": release_call_url,
    }


def generate_full_markdown(badge, countdown_info, release_config):
    version = release_config.get("next_version", "?")
    release_date_str = countdown_info["release_date"]
    days = countdown_info["days_remaining"]

    release_call_url = badge["link_url"]

    lines = [
        "## Monthly Release & Community Call",
        "",
    ]

    if countdown_info["is_released"] and not countdown_info["is_today"]:
        past = abs(days)
        lines.append(
            f"The [ClickHouse **{version}** Release Call]({release_call_url}) "
            f"was on {release_date_str} ({past} day{'s' if past != 1 else ''} ago)."
        )
    elif countdown_info["is_today"]:
        lines.append(
            f"Join us for the [ClickHouse **{version}** Release Call]({release_call_url}) "
            f"**today**, {release_date_str}!"
        )
    else:
        lines.append(
            f"Join us for the [ClickHouse **{version}** Release Call]({release_call_url}) "
            f"on {release_date_str} ({days} day{'s' if days != 1 else ''} from now)."
        )

    lines.extend([
        "",
        badge["markdown"],
        "",
        "Watch all release presentations and videos at "
        "[ClickHouse Theater](https://presentations.clickhouse.com/) and "
        "[YouTube Playlist](https://www.youtube.com/playlist?list=PL0Z2YDlm0b3jAlSy1JxyP8zluvXaN3nxU).",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="ClickHouse Release Countdown Automation"
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=str(DEFAULT_CONFIG),
        help=f"Path to config.yaml (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--badge-only",
        action="store_true",
        help="Print only the Markdown badge URL",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print full Markdown snippet for the Monthly Release section",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output for automation",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    config = load_yaml(args.config)
    release_config = config.get("release", {})
    if not release_config:
        print("Error: no 'release' section found in config", file=sys.stderr)
        sys.exit(1)

    next_release_date_str = release_config.get("next_release_date")
    if not next_release_date_str:
        print("Error: 'next_release_date' not set in config", file=sys.stderr)
        sys.exit(1)

    try:
        release_date = parse_release_date(next_release_date_str)
    except ValueError as e:
        print(f"Error: invalid date format in config: {e}", file=sys.stderr)
        sys.exit(1)

    countdown_info = compute_countdown(release_date)
    badge = generate_countdown_badge(countdown_info, release_config)

    if args.json:
        output = {
            "countdown": countdown_info,
            "badge": badge,
            "release": release_config,
        }
        print(json.dumps(output, indent=2))
    elif args.badge_only:
        print(badge["markdown"])
    elif args.markdown:
        print(generate_full_markdown(badge, countdown_info, release_config))
    else:
        print(f"Next release: ClickHouse {release_config.get('next_version', '?')}")
        print(f"Release date: {countdown_info['release_date']}")
        print(f"Days remaining: {countdown_info['days_remaining']}")
        print()
        print("Badge Markdown:")
        print(badge["markdown"])


if __name__ == "__main__":
    main()