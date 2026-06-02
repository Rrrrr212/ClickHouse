#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from config_loader import load_config
from release_countdown import build_badge_markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "community" / "config.yaml"
DEFAULT_README_PATH = ROOT / "README.md"


def markdown_link(label: str, url: str) -> str:
    return f"[{label}]({url})"


def render_useful_links(config: dict) -> str:
    community_links = config["community"]["links"]
    slack = community_links["slack"]
    telegram = community_links["telegram"]
    youtube = community_links["youtube"]
    blog = community_links["blog"]
    bluesky = community_links["bluesky"]
    x_link = community_links["x"]

    lines = [
        "## Useful Links",
        "",
        "* [Official website](https://clickhouse.com/) has a quick high-level overview of ClickHouse on the main page.",
        "* [ClickHouse Cloud](https://clickhouse.cloud) ClickHouse as a service, built by the creators and maintainers.",
        "* [Tutorial](https://clickhouse.com/docs/getting_started/tutorial/) shows how to set up and query a small ClickHouse cluster.",
        "* [Documentation](https://clickhouse.com/docs/) provides more in-depth information.",
        (
            f"* {markdown_link(slack['label'], slack['url'])} and "
            f"{markdown_link(telegram['label'], telegram['url'])} "
            f"allow chatting with ClickHouse users in real-time."
        ),
        f"* {markdown_link(youtube['label'], youtube['url'])} has a lot of content about ClickHouse in video format.",
        f"* {markdown_link(blog['label'], blog['url'])} contains various ClickHouse-related articles, as well as announcements and reports about events.",
        (
            f"* {markdown_link(bluesky['label'], bluesky['url'])} and "
            f"{markdown_link(x_link['label'], x_link['url'])} for short news."
        ),
        "* [ClickHouse Theater](https://presentations.clickhouse.com/) contains presentations and videos about ClickHouse.",
        "* [Code Browser (github.dev)](https://github.dev/ClickHouse/ClickHouse) with syntax highlighting, powered by github.dev.",
        "* [Contacts](https://clickhouse.com/company/contact) can help to get your questions answered if there are any.",
    ]
    return "\n".join(lines)


def format_human_date(raw_date: str) -> str:
    parsed_date = date.fromisoformat(raw_date)
    return f"{parsed_date.strftime('%B')} {parsed_date.day}, {parsed_date.year}"


def render_release_section(config: dict) -> str:
    release = config["release"]
    version = release["version"]
    formatted_date = format_human_date(release["date"])
    call_url = release.get("call_url", "https://clickhouse.com/company/news-events")
    badge = build_badge_markdown(config)

    lines = [
        "## Monthly Release & Community Call",
        "",
        badge,
        "",
        f"Join us for the [ClickHouse **{version}** Release Call]({call_url}) on {formatted_date}.",
        "",
        (
            "Watch all release presentations and videos at "
            f"[ClickHouse Theater]({release['theater_url']}) and "
            f"[YouTube Playlist]({release['youtube_playlist_url']})."
        ),
    ]
    return "\n".join(lines)


def replace_section(readme: str, start_heading: str, end_heading: str, replacement: str) -> str:
    start_index = readme.index(start_heading)
    end_index = readme.index(end_heading, start_index)
    return f"{readme[:start_index]}{replacement.rstrip()}\n\n{readme[end_index:]}"


def render_readme(config: dict, readme: str) -> str:
    updated = replace_section(
        readme,
        "## Useful Links",
        "## Monthly Release & Community Call",
        render_useful_links(config),
    )
    updated = replace_section(
        updated,
        "## Monthly Release & Community Call",
        "## Upcoming Events",
        render_release_section(config),
    )
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render README community and release sections")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the community configuration file",
    )
    parser.add_argument(
        "--readme",
        default=str(DEFAULT_README_PATH),
        help="Path to the README file to render",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with a non-zero code when the README is not up to date",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    readme_path = Path(args.readme)
    config = load_config(config_path)
    original_readme = readme_path.read_text(encoding="utf-8")
    rendered_readme = render_readme(config, original_readme)

    if args.check:
        return 0 if rendered_readme == original_readme else 1

    readme_path.write_text(rendered_readme, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
