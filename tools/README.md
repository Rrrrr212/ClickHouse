# ClickHouse Tools

This directory contains standalone tooling for the ClickHouse project, separated
from the core C++ codebase for better modularity and maintainability.

## Directory Structure

```
tools/
├── toolchain/          # Installation toolchain
│   ├── installer/      # ClickHouse installer binary and scripts
│   │   ├── Install.cpp
│   │   ├── install.sh
│   │   └── templates/
│   └── verifier/       # Installation verification tool
│       └── InstallVerify.cpp
├── community/          # Community management tools
│   ├── community.yaml  # Centralized community links configuration
│   └── generate_community_links.py  # Link generator
└── release/            # Release management tools
    ├── release_checklist.yaml  # Release checklist configuration
    ├── release_checklist.py    # Release checklist executor
    └── generate_release_notes.py  # Release notes generator
```

## Modules

### Toolchain (`tools/toolchain/`)

The installation toolchain provides a standalone installation mechanism for
ClickHouse, independent of the `curl | sh` pattern:

- `installer/install.sh` - Standalone shell-based installer
- `installer/Install.cpp` - C++ installation binary (used by `clickhouse install`)
- `verifier/InstallVerify.cpp` - Verifies that an installation is correct

### Community (`tools/community/`)

Centralized management of community channel links:

- `community.yaml` - Single source of truth for all community links
- `generate_community_links.py` - Generates links in various formats (README, HTML, Markdown)

### Release (`tools/release/`)

Scriptable release management:

- `release_checklist.yaml` - Executable checklist configuration
- `release_checklist.py` - Interactive checklist executor
- `generate_release_notes.py` - Automated release notes generation