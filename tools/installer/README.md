# ClickHouse Installer Tool

This directory contains the official ClickHouse installation scripts and tools.

## Directory Structure

```
tools/installer/
├── README.md
├── install.sh          # Main installation script
├── config.sh           # Configuration file
├── detect.sh           # System detection utilities
├── download.sh         # Package download functions
├── verify.sh           # GPG verification utilities
└── install_*.sh        # Platform-specific installers
```

## Usage

### Quick Install

```bash
curl https://clickhouse.com/ | sh
```

### Advanced Usage

```bash
# Download and install specific version
./install.sh --version 26.5.1.882

# Install only specific components
./install.sh --components server,client

# Dry run (preview what would be installed)
./install.sh --dry-run
```

## Platform Support

- Linux (Debian/Ubuntu, RHEL/CentOS, SUSE, Arch)
- macOS
- FreeBSD

## Configuration

See `config.sh` for configurable options including:
- Package repository URLs
- Installation paths
- GPG key locations
- Components to install by default
