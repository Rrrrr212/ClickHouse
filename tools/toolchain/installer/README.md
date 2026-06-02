# ClickHouse Installer Toolchain

This directory contains the installation tooling for ClickHouse.

## Overview

The installer toolchain provides:
- Automated installation from binary packages
- System configuration and user/group creation
- Default configuration file generation
- Capability and permission setup
- Service registration (systemd, upstart, sysv)

## Components

- `clickhouse-install` - Main installation binary
- `install-scripts/` - Helper shell scripts for different distributions
- `templates/` - Configuration file templates

## Usage

```bash
# Install ClickHouse from a downloaded binary
./clickhouse-install [OPTIONS]

# Options:
#   --prefix PATH         Installation prefix (default: /usr)
#   --user USER            User name (default: clickhouse)
#   --group GROUP          Group name (default: clickhouse)
#   --no-systemd           Skip systemd service installation
#   --dry-run              Show what would be done
```

## Building

Build as part of the full ClickHouse build:

```bash
cmake .. -DENABLE_TOOLCHAIN=ON
make clickhouse-install
```
