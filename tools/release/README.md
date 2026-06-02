# ClickHouse Release Automation Tools

This directory contains tools for automating the ClickHouse monthly release process.

## Features

- Pre-release checklist automation
- Changelog generation
- Version bumping
- Release branch management
- Post-release tasks
- Notification integration

## Directory Structure

```
tools/release/
├── README.md
├── config.yaml              # Release configuration
├── checklist.yaml           # Pre-release checklist definition
├── release_manager.py       # Main release orchestrator
├── preflight_checks.py      # Pre-release validation
├── changelog_helper.py      # Changelog generation utilities
├── notifications.py         # Notification senders (Slack, etc.)
└── scripts/
    ├── bump_version.sh
    ├── create_branch.sh
    └── post_release.sh
```

## Usage

### Start a New Release

```bash
python3 release_manager.py --type new --version 26.6
```

### Create a Patch Release

```bash
python3 release_manager.py --type patch --version 26.5.2
```

### Run Pre-flight Checks Only

```bash
python3 release_manager.py --checks-only
```

## Configuration

See `config.yaml` for all configurable options.

## Pre-flight Checklist

The pre-release checklist includes:
- CI status verification
- Documentation update checks
- Performance test results
- Security audit
- Release notes preparation
- Community announcement drafting
