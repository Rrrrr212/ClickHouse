#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install it with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "community" / "config.yaml"
README_PATH = REPO_ROOT / "README.md"

SECTION_BEGIN = "<!-- COMMUNITY_LINKS_BEGIN -->"
SECTION_END = "<!-- COMMUNITY_LINKS_END -->"


def load_config(config_path=None):
    path = Path(config_path) if config_path else CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_useful_links(links):
    primary = []
    docs = []
    chat = []
    social = []
    media = []
    development = []
    events = []

    for link in links:
        cat = link.get("category", "primary")
        if cat == "primary":
            primary.append(link)
        elif cat == "docs":
            docs.append(link)
        elif cat == "chat":
            chat.append(link)
        elif cat == "social":
            social.append(link)
        elif cat == "media":
            media.append(link)
        elif cat == "development":
            development.append(link)
        elif cat == "events":
            events.append(link)

    lines = []

    for link in primary + docs + development + chat + social + media + events:
        name = link["name"]
        url = link["url"]
        desc = link.get("description", "")
        if desc:
            lines.append(f"* [{name}]({url}) {desc}")
        else:
            lines.append(f"* [{name}]({url})")

    return "\n".join(lines)


def render_release_section(config):
    release = config.get("release", {}).get("next", {})
    if not release:
        return ""

    version = release.get("version", "")
    date = release.get("date", "")
    event_url = release.get("event_url", "")

    if event_url:
        line = f'Join us for the [ClickHouse **{version}** Release Call]({event_url}) on {date}.'
    else:
        line = f"Join us for the ClickHouse **{version}** Release Call on {date}."

    return line


def update_readme(config, readme_path=None, dry_run=False):
    path = Path(readme_path) if readme_path else README_PATH
    content = path.read_text(encoding="utf-8")

    links_section = render_useful_links(config.get("community", {}).get("links", []))
    release_line = render_release_section(config)

    new_content = content

    if SECTION_BEGIN in content and SECTION_END in content:
        pattern = re.compile(
            re.escape(SECTION_BEGIN) + r".*?" + re.escape(SECTION_END),
            re.DOTALL,
        )
        replacement = SECTION_BEGIN + "\n" + links_section + "\n" + SECTION_END
        new_content = pattern.sub(replacement, content)
    else:
        useful_links_header = "## Useful Links"
        if useful_links_header in new_content:
            next_header_match = re.search(
                r"\n##\s", new_content[new_content.index(useful_links_header) + len(useful_links_header) :]
            )
            if next_header_match:
                end_pos = new_content.index(useful_links_header) + len(useful_links_header) + next_header_match.start()
                new_content = (
                    new_content[: new_content.index(useful_links_header)]
                    + useful_links_header
                    + "\n\n"
                    + SECTION_BEGIN
                    + "\n"
                    + links_section
                    + "\n"
                    + SECTION_END
                    + "\n\n"
                    + new_content[end_pos:]
                )
            else:
                new_content = (
                    new_content[: new_content.index(useful_links_header)]
                    + useful_links_header
                    + "\n\n"
                    + SECTION_BEGIN
                    + "\n"
                    + links_section
                    + "\n"
                    + SECTION_END
                    + "\n"
                )

    release_header = "## Monthly Release & Community Call"
    if release_header in new_content and release_line:
        release_section_start = new_content.index(release_header) + len(release_header)
        next_release_header = re.search(r"\n##\s", new_content[release_section_start:])
        if next_release_header:
            release_section_end = release_section_start + next_release_header.start()
            new_content = (
                new_content[:release_section_start]
                + "\n\n"
                + release_line
                + "\n\n"
                + new_content[release_section_end:]
            )

    if dry_run:
        print(new_content)
        return False

    if new_content != content:
        path.write_text(new_content, encoding="utf-8")
        print(f"Updated {path}")
        return True
    else:
        print("No changes needed.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Render community links from config.yaml into README.md")
    parser.add_argument("--config", default=None, help="Path to config.yaml (default: community/config.yaml)")
    parser.add_argument("--readme", default=None, help="Path to README.md (default: README.md)")
    parser.add_argument("--dry-run", action="store_true", help="Print result without writing to file")
    parser.add_argument(
        "--section-only",
        action="store_true",
        help="Only output the Useful Links section content (for embedding)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    if args.section_only:
        print(render_useful_links(config.get("community", {}).get("links", [])))
        return

    update_readme(config, args.readme, args.dry_run)


if __name__ == "__main__":
    main()
