#!/usr/bin/env python3
"""
Render community links from config.yaml into Markdown for the README.

Reads community/config.yaml, extracts the community section, and generates
Markdown bullet list entries. Supports injecting the rendered block into
the README.md between designated anchor comments.

Usage:
    python3 community/render_community.py                # print to stdout
    python3 community/render_community.py --inject       # update README.md
    python3 community/render_community.py -o output.md   # write to file
"""

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ANCHOR_START = "<!-- COMMUNITY_LINKS_START -->"
ANCHOR_END = "<!-- COMMUNITY_LINKS_END -->"

# Mapping from config key to the display order and grouping
LINK_ORDER = [
    "official_website",
    "clickhouse_cloud",
    "tutorial",
    "documentation",
    "youtube",
    "clickhouse_theater",
    "slack",
    "telegram",
    "blog",
    "bluesky",
    "x",
    "github_dev",
    "contacts",
]

PAIRED_LINKS = {
    ("slack", "telegram"): "allow chatting with ClickHouse users in real-time",
    ("bluesky", "x"): "for short news",
}


def load_yaml(path):
    try:
        import yaml
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except ImportError:
        print("Error: PyYAML is required. Install it with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)


def render_community_links(config):
    community = config.get("community", {})
    if not community:
        return ""

    lines = []
    rendered = set()

    for pair, shared_desc in PAIRED_LINKS.items():
        if all(k in community for k in pair):
            a = community[pair[0]]
            b = community[pair[1]]
            lines.append(
                f"* [{a['name']}]({a['url']}) and "
                f"[{b['name']}]({b['url']}) {shared_desc}."
            )
            rendered.update(pair)

    for key in LINK_ORDER:
        if key in rendered:
            continue
        if key not in community:
            continue
        entry = community[key]
        desc = entry.get("description", "")
        if desc:
            lines.append(f"* [{entry['name']}]({entry['url']}) {desc}.")
        else:
            lines.append(f"* [{entry['name']}]({entry['url']}).")

    return "\n".join(lines)


def inject_into_readme(readme_path, links_block):
    with open(readme_path, "r") as f:
        content = f.read()

    pattern = re.compile(
        re.escape(ANCHOR_START) + r".*?" + re.escape(ANCHOR_END),
        re.DOTALL,
    )

    replacement = ANCHOR_START + "\n" + links_block + "\n" + ANCHOR_END

    if pattern.search(content):
        new_content = pattern.sub(replacement, content)
    else:
        new_content = content + "\n" + replacement + "\n"

    with open(readme_path, "w") as f:
        f.write(new_content)


def main():
    parser = argparse.ArgumentParser(
        description="Render ClickHouse community links from config.yaml to Markdown"
    )
    parser.add_argument(
        "--inject",
        action="store_true",
        help="Inject the rendered links block into README.md between anchor comments",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Write output to file instead of stdout",
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=str(REPO_ROOT / "community" / "config.yaml"),
        help="Path to config.yaml (default: community/config.yaml)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    config = load_yaml(args.config)
    links_block = render_community_links(config)

    if args.inject:
        readme_path = REPO_ROOT / "README.md"
        if not readme_path.exists():
            print(f"Error: README.md not found at {readme_path}", file=sys.stderr)
            sys.exit(1)
        inject_into_readme(str(readme_path), links_block)
        print(f"Injected community links block into {readme_path}")
    elif args.output:
        with open(args.output, "w") as f:
            f.write(links_block + "\n")
        print(f"Written to {args.output}")
    else:
        print(links_block)


if __name__ == "__main__":
    main()