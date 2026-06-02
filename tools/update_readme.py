#!/usr/bin/env python3

import yaml
import re
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "community" / "config.yaml"
README_PATH = Path(__file__).parent.parent / "README.md"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def update_useful_links(readme_content, config):
    links_section = []

    for key, link in config["official_links"].items():
        links_section.append(f"* [{link['name']}]({link['url']})")

    for key, link in config["community_links"].items():
        links_section.append(f"* [{link['name']}]({link['url']})")

    links_section.append("* [Code Browser (github.dev)](https://github.dev/ClickHouse/ClickHouse) with syntax highlighting, powered by github.dev.")

    new_links = "\n".join(links_section)
    pattern = re.compile(r"## Useful Links\n\n.*?\n\n##", re.DOTALL)
    replacement = f"## Useful Links\n\n{new_links}\n\n##"
    return pattern.sub(replacement, readme_content)


def update_release_call(readme_content, config):
    release = config["release"]
    next_date = datetime.strptime(release["next_date"], "%Y-%m-%d")
    date_str = next_date.strftime("%B %d, %Y")
    release_text = f"Join us for the [ClickHouse **{release['version']}** Release Call]({release['event_url']}) on {date_str}."

    pattern = re.compile(r"Join us for the \[ClickHouse \*\*.*?\*\* Release Call\]\(.*?\) on .*?\.")
    return pattern.sub(release_text, readme_content)


def main():
    config = load_config()

    with open(README_PATH, "r", encoding="utf-8") as f:
        readme_content = f.read()

    readme_content = update_useful_links(readme_content, config)
    readme_content = update_release_call(readme_content, config)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"README.md updated successfully from {CONFIG_PATH}")


if __name__ == "__main__":
    main()
