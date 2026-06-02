#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "community" / "config.yaml"
DEFAULT_README = Path(__file__).resolve().parents[1] / "README.md"
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from release_countdown import build_badge_markdown, load_config

COMMUNITY_START = "<!-- COMMUNITY_LINKS:START -->"
COMMUNITY_END = "<!-- COMMUNITY_LINKS:END -->"
RELEASE_START = "<!-- RELEASE_COUNTDOWN:START -->"
RELEASE_END = "<!-- RELEASE_COUNTDOWN:END -->"
COMMUNITY_ORDER = ["youtube", "slack", "telegram", "blog", "bluesky", "x"]


def render_community_links(config: dict) -> str:
    community_links = config["community"]
    lines = []
    for name in COMMUNITY_ORDER:
        item = community_links[name]
        lines.append(f"* [{item['label']}]({item['url']}) — {item['description']}")
    return "\n".join(lines)


def render_release_section(config: dict) -> str:
    release = config["next_release"]
    badge = build_badge_markdown(config)
    lines = [
        badge,
        "",
        f"Join us for the [ClickHouse **{release['version']}** Release Call]({release['event_url']}) on {release['date']}.",
        "",
        "Watch all release presentations and videos at [ClickHouse Theater](https://presentations.clickhouse.com/) and [YouTube Playlist](https://www.youtube.com/playlist?list=PL0Z2YDlm0b3jAlSy1JxyP8zluvXaN3nxU).",
    ]
    return "\n".join(lines)


def replace_block(content: str, start_marker: str, end_marker: str, replacement: str) -> str:
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    block = f"{start_marker}\n{replacement}\n{end_marker}"
    updated_content, count = pattern.subn(block, content, count=1)
    if count != 1:
        raise ValueError(f"Unable to find block {start_marker} ... {end_marker}")
    return updated_content


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render community links and release countdown into README")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to community config.yaml")
    parser.add_argument("--readme", type=Path, default=DEFAULT_README, help="Path to README.md")
    parser.add_argument("--stdout", action="store_true", help="Print rendered README instead of writing it")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    readme_content = args.readme.read_text(encoding="utf-8")
    readme_content = replace_block(readme_content, COMMUNITY_START, COMMUNITY_END, render_community_links(config))
    readme_content = replace_block(readme_content, RELEASE_START, RELEASE_END, render_release_section(config))

    if args.stdout:
        print(readme_content, end="")
        return 0

    args.readme.write_text(readme_content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
