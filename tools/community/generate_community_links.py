#!/usr/bin/env python3
"""
ClickHouse Community Links Generator

Generates formatted community links from the centralized community.yaml
configuration file. Supports multiple output formats for use in README,
documentation, and other marketing materials.

Usage:
    python3 tools/community/generate_community_links.py --format readme
    python3 tools/community/generate_community_links.py --format html
    python3 tools/community/generate_community_links.py --format markdown
    python3 tools/community/generate_community_links.py --validate
    python3 tools/community/generate_community_links.py --check-readme
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def load_community_config(config_path: Optional[str] = None) -> Dict:
    if config_path is None:
        config_path = Path(__file__).parent / "community.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError("Empty community configuration")

    required_keys = ["version", "categories"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required key in community config: {key}")

    return config


def validate_config(config: Dict) -> List[str]:
    errors = []

    for category in config.get("categories", []):
        if "id" not in category:
            errors.append(f"Category missing 'id': {category.get('label', 'unknown')}")
        if "entries" not in category:
            errors.append(f"Category '{category.get('id', 'unknown')}' missing 'entries'")

        for entry in category.get("entries", []):
            if "name" not in entry:
                errors.append(f"Entry in '{category.get('id')}' missing 'name'")
            if "url" not in entry:
                errors.append(f"Entry '{entry.get('name', 'unknown')}' missing 'url'")

    return errors


def format_readme_links(config: Dict) -> str:
    lines = []
    lines.append("## Useful Links")
    lines.append("")

    for category in config.get("categories", []):
        if category.get("id") in ("security", "resources"):
            continue

        entries = category.get("entries", [])
        for entry in entries:
            name = entry["name"]
            url = entry["url"]
            description = entry.get("description", "")
            line = f"* [{name}]({url}) {description}"
            lines.append(line)

    lines.append("")
    return "\n".join(lines)


def format_markdown_table(config: Dict) -> str:
    lines = []
    lines.append("| Category | Channel | Description | URL |")
    lines.append("|----------|---------|-------------|-----|")

    for category in config.get("categories", []):
        label = category.get("label", category.get("id", ""))
        for entry in category.get("entries", []):
            name = entry["name"]
            url = entry["url"]
            description = entry.get("description", "")
            lines.append(f"| {label} | {name} | {description} | [{name}]({url}) |")

    return "\n".join(lines)


def format_html_links(config: Dict) -> str:
    lines = ['<ul class="community-links">']

    for category in config.get("categories", []):
        label = category.get("label", category.get("id", ""))
        lines.append(f'  <li class="community-category">')
        lines.append(f"    <strong>{label}</strong>")
        lines.append('    <ul>')

        for entry in category.get("entries", []):
            name = entry["name"]
            url = entry["url"]
            description = entry.get("description", "")
            icon = entry.get("icon", "")
            lines.append(
                f'      <li><a href="{url}" title="{description}"'
                f' class="community-link community-link-{icon}">{name}</a></li>'
            )

        lines.append("    </ul>")
        lines.append("  </li>")

    lines.append("</ul>")
    return "\n".join(lines)


def check_readme_consistency(config: Dict, readme_path: Optional[str] = None) -> List[str]:
    if readme_path is None:
        readme_path = Path(__file__).parent.parent.parent / "README.md"

    issues = []

    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()

    for category in config.get("categories", []):
        for entry in category.get("entries", []):
            if "url" in entry and entry["url"] not in readme_content:
                issues.append(
                    f"URL for '{entry['name']}' ({entry['url']}) not found in README.md"
                )

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Generate community links from centralized configuration"
    )
    parser.add_argument(
        "--format",
        choices=["readme", "markdown", "html", "json"],
        default="readme",
        help="Output format (default: readme)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to community.yaml (default: tools/community/community.yaml)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the community configuration file",
    )
    parser.add_argument(
        "--check-readme",
        action="store_true",
        help="Check if README.md contains all community links from the config",
    )
    args = parser.parse_args()

    try:
        config = load_community_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)

    if args.validate:
        errors = validate_config(config)
        if errors:
            print("Configuration validation FAILED:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("Configuration validation PASSED")
            print(f"Version: {config.get('version')}")
            print(f"Categories: {len(config.get('categories', []))}")
            total_entries = sum(
                len(cat.get("entries", [])) for cat in config.get("categories", [])
            )
            print(f"Total entries: {total_entries}")
            sys.exit(0)

    if args.check_readme:
        issues = check_readme_consistency(config)
        if issues:
            print("README.md consistency check FAILED:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print("README.md consistency check PASSED")
            sys.exit(0)

    if args.format == "readme":
        output = format_readme_links(config)
    elif args.format == "markdown":
        output = format_markdown_table(config)
    elif args.format == "html":
        output = format_html_links(config)
    elif args.format == "json":
        import json
        output = json.dumps(config, indent=2, ensure_ascii=False)
    else:
        output = format_readme_links(config)

    print(output)


if __name__ == "__main__":
    main()