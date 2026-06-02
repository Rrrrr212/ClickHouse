# ClickHouse Release Process

Automated release checklist and workflow for monthly ClickHouse releases.

## Quick Start

Run the full release process:

```bash
./release/release.sh --version 26.5
```

Dry-run to preview steps:

```bash
./release/release.sh --version 26.5 --dry-run
```

## Release Steps

The release process consists of 8 automated steps:

| Step | Name | Description |
|------|------|-------------|
| 1 | `preflight` | Pre-release checks (Git state, tools, version) |
| 2 | `build` | Build release binaries |
| 3 | `test` | Run test suite |
| 4 | `package` | Create packages (deb, rpm, tgz, docker) |
| 5 | `sign` | Sign packages with GPG |
| 6 | `publish` | Publish to repositories |
| 7 | `announce` | Generate announcements |
| 8 | `post-release` | Post-release tasks |

## Skipping Steps

Skip specific steps with `--skip`:

```bash
./release/release.sh --version 26.5 --skip test,publish
```

## Options

| Option | Description |
|--------|-------------|
| `--version <VERSION>` | Release version (required) |
| `--branch <BRANCH>` | Release branch (default: master) |
| `--channel <stable\|lts>` | Release channel (default: stable) |
| `--dry-run` | Show steps without executing |
| `--skip <steps>` | Comma-separated list of steps to skip |

## Examples

Full LTS release:

```bash
./release/release.sh --version 24.8 --channel lts
```

Build and package only (skip tests and publish):

```bash
./release/release.sh --version 26.5 --skip test,publish,announce,post-release
```

Release from specific branch:

```bash
./release/release.sh --version 26.5 --branch release-26.5
```

## Release Artifacts

After a successful release, artifacts are stored in:

```
tmp/release_<timestamp>/
├── packages/
│   ├── clickhouse-<VERSION>-amd64.tgz
│   ├── clickhouse-<VERSION>-amd64.tgz.asc
│   ├── SHA256SUMS
│   ├── SHA256SUMS.asc
│   └── Dockerfile
└── announcements/
    ├── release_notes.md
    └── social_posts.md
```

## Manual Tasks

Some tasks still require manual intervention:

- DEB/RPM package repository publishing
- Docker image push to Docker Hub
- CHANGELOG updates
- Release call scheduling
- Blog post creation

These are documented in the release output and announcement templates.
