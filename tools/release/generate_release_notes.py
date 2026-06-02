#!/usr/bin/env python3
"""
ClickHouse Release Notes Generator

Generates release notes from merged pull requests between two versions.
Fetches PRs from GitHub, categorizes them according to ClickHouse's
changelog categories, and produces formatted release notes in Markdown.

Usage:
    python3 tools/release/generate_release_notes.py --from v26.4 --to v26.5
    python3 tools/release/generate_release_notes.py --output RELEASE_NOTES.md
    python3 tools/release/generate_release_notes.py --from v26.4 --to v26.5 --format github
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

CATEGORIES = {
    "New Feature": {
        "emoji": "✨",
        "description": "New features",
        "order": 1,
    },
    "Experimental Feature": {
        "emoji": "🧪",
        "description": "Experimental features",
        "order": 2,
    },
    "Improvement": {
        "emoji": "🚀",
        "description": "Improvements to existing functionality",
        "order": 3,
    },
    "Performance Improvement": {
        "emoji": "⚡",
        "description": "Performance improvements",
        "order": 4,
    },
    "Backward Incompatible Change": {
        "emoji": "⚠️",
        "description": "Backward incompatible changes",
        "order": 5,
    },
    "Build/Testing/Packaging Improvement": {
        "emoji": "🧰",
        "description": "Build, testing, and packaging improvements",
        "order": 6,
    },
    "Documentation": {
        "emoji": "📚",
        "description": "Documentation improvements",
        "order": 7,
    },
    "Critical Bug Fix": {
        "emoji": "🔴",
        "description": "Critical bug fixes (crash, data loss, RBAC)",
        "order": 8,
    },
    "Bug Fix": {
        "emoji": "🐛",
        "description": "Bug fixes for user-visible misbehavior",
        "order": 9,
    },
    "CI Fix or improvement": {
        "emoji": "🔧",
        "description": "CI fixes and improvements",
        "order": 10,
        "hide_in_release_notes": True,
    },
    "Not for changelog": {
        "emoji": "⚫",
        "description": "Not for changelog",
        "order": 11,
        "hide_in_release_notes": True,
    },
}

GITHUB_API = "https://api.github.com"
REPO = "ClickHouse/ClickHouse"


def get_github_token() -> Optional[str]:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    token_path = Path.home() / ".github_token"
    if token_path.exists():
        return token_path.read_text().strip()
    return None


def get_headers() -> Dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def get_merged_prs_between(version_from: str, version_to: str) -> List[Dict]:
    url = f"{GITHUB_API}/repos/{REPO}/compare/{version_from}...{version_to}"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    data = response.json()

    pr_numbers = set()
    for commit in data.get("commits", []):
        message = commit.get("commit", {}).get("message", "")
        if "Merge #" in message or "PR #" in message:
            import re
            matches = re.findall(r'#(\d+)', message)
            for match in matches:
                pr_numbers.add(int(match))

    prs = []
    for pr_number in sorted(pr_numbers):
        url = f"{GITHUB_API}/repos/{REPO}/pulls/{pr_number}"
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            pr = response.json()
            if pr.get("merged", False):
                prs.append(pr)

    return sorted(prs, key=lambda p: p["number"])


def categorize_prs(prs: List[Dict]) -> Dict[str, List[Dict]]:
    categorized: Dict[str, List[Dict]] = {cat: [] for cat in CATEGORIES.keys()}

    for pr in prs:
        category = "Not for changelog"
        if "labels" in pr and pr["labels"]:
            for label in pr["labels"]:
                label_name = label["name"]
                if label_name in CATEGORIES:
                    category = label_name
                    break
        categorized[category].append(pr)

    return categorized


def format_markdown_release_notes(categorized: Dict[str, List[Dict]], version: str, date: str) -> str:
    lines = [
        f"# ClickHouse {version} Release Notes",
        "",
        f"Released: {date}",
        "",
    ]

    sorted_categories = sorted(
        CATEGORIES.items(),
        key=lambda x: x[1]["order"],
    )

    for category_name, category_info in sorted_categories:
        prs = categorized.get(category_name, [])
        if not prs:
            continue
        if category_info.get("hide_in_release_notes", False):
            continue

        emoji = category_info["emoji"]
        description = category_info["description"]
        lines.append(f"## {emoji} {category_name} - {description}")
        lines.append("")

        for pr in prs:
            number = pr["number"]
            title = pr["title"]
            author = pr["user"]["login"]
            url = pr["html_url"]
            lines.append(f"- {title} ([#{number}]({url}) by @{author})")
        lines.append("")

    lines.append("## 🧑‍💻 Contributors")
    lines.append("")

    contributors = set()
    for pr_list in categorized.values():
        for pr in pr_list:
            if pr:
                contributors.add("@" + pr["user"]["login"])

    lines.append(f"This release includes contributions from **{len(contributors)} contributors**.")
    lines.append(f"Thank you to all our contributors!")
    lines.append("")
    lines.append(f"Contributors: {' '.join(sorted(contributors))}")
    lines.append("")

    return "\n".join(lines)


def format_github_release(categorized: Dict[str, List[Dict]], version: str) -> str:
    lines = [f"ClickHouse {version} is ready!"]
    lines.append("")
    lines.append("## Summary")
    lines.append("")

    sorted_categories = sorted(
        CATEGORIES.items(),
        key=lambda x: x[1]["order"],
    )

    for category_name, category_info in sorted_categories:
        prs = categorized.get(category_name, [])
        if not prs or category_info.get("hide_in_release_notes", False):
            continue
        emoji = category_info["emoji"]
        count = len(prs)
        lines.append(f"- {emoji} **{category_name}**: {count} pull requests")
    lines.append("")
    lines.append("## Highlights")
    lines.append("")
    lines.append("_(Add highlights here manually before publishing)_")
    lines.append("")
    lines.append("## Download")
    lines.append("")
    lines.append(f"- [Official Website](https://clickhouse.com/downloads?version={version})")
    lines.append(f"- [Docker](https://hub.docker.com/r/clickhouse/clickhouse-server/tags?page=1&name={version})")
    lines.append("")
    lines.append("## Full Changelog")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate release notes from merged PRs",
    )
    parser.add_argument(
        "--from",
        dest="from_version",
        required=True,
        help="Starting version (e.g., v26.4)",
    )
    parser.add_argument(
        "--to",
        dest="to_version",
        required=True,
        help="Ending version (e.g., v26.5)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "github"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--cache-file",
        default=None,
        help="Cache PR data to file for faster reruns",
    )
    args = parser.parse_args()

    if args.cache_file and Path(args.cache_file).exists():
        print(f"Loading cached PR data from {args.cache_file}")
        with open(args.cache_file, "r", encoding="utf-8") as f:
            prs = json.load(f)
    else:
        print(f"Fetching merged PRs between {args.from_version} and {args.to_version}...")
        prs = get_merged_prs_between(args.from_version, args.to_version)

        if args.cache_file:
            with open(args.cache_file, "w", encoding="utf-8") as f:
                json.dump([{
                    "number": pr["number"],
                    "title": pr["title"],
                    "html_url": pr["html_url"],
                    "user": {"login": pr["user"]["login"]},
                    "labels": pr.get("labels", []),
                    "merged": pr.get("merged", True),
                } for pr in prs], f, indent=2)

    print(f"Found {len(prs)} merged pull requests")

    categorized = categorize_prs(prs)

    today = datetime.now().strftime("%B %d, %Y")
    version_clean = args.to_version.lstrip('v')

    if args.format == "markdown":
        content = format_markdown_release_notes(categorized, version_clean, today)
    elif args.format == "github":
        content = format_github_release(categorized, version_clean)
    else:
        content = format_markdown_release_notes(categorized, version_clean, today)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Wrote release notes to {args.output}")
    else:
        print(content)


if __name__ == "__main__":
    main()