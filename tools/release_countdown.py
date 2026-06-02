#!/usr/bin/env python3

import yaml
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "community" / "config.yaml"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_countdown(target_date_str):
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = target_date - now

    if delta.total_seconds() < 0:
        return "Released!"
    elif delta.days > 0:
        return f"{delta.days} days"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        return f"{hours} hours"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        return f"{minutes} minutes"
    else:
        return "Any minute!"


def generate_badge(label, message, color):
    encoded_label = label.replace(" ", "%20")
    encoded_message = message.replace(" ", "%20")
    return f"![{label}: {message}](https://img.shields.io/badge/{encoded_label}-{encoded_message}-{color}?style=for-the-badge)"


def main():
    config = load_config()
    release = config["release"]
    countdown = calculate_countdown(release["next_date"])

    if countdown == "Released!":
        badge = generate_badge("Release", countdown, "success")
    else:
        badge = generate_badge(f"Next Release ({release['version']})", countdown, "blue")

    print(badge)

    return 0


if __name__ == "__main__":
    sys.exit(main())
