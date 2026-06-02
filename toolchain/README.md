# ClickHouse Toolchain

Unified toolchain scripts for ClickHouse development, installation, testing, and release.

## Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `install.sh` | Multi-platform installation script | `./toolchain/install.sh --channel stable` |
| `build.sh` | Unified build script | `./toolchain/build.sh --type release` |
| `test.sh` | Test suite runner | `./toolchain/test.sh --suite stateless` |

## Installation

Quick install (auto-detects OS and package manager):

```bash
./toolchain/install.sh
```

Install specific version:

```bash
./toolchain/install.sh --version 24.8.1.2742
```

Install via Docker:

```bash
./toolchain/install.sh --method docker
```

Dry-run to see what would be executed:

```bash
./toolchain/install.sh --dry-run
```

## Building

Release build:

```bash
./toolchain/build.sh --type release
```

Debug build:

```bash
./toolchain/build.sh --type debug
```

Clean build:

```bash
./toolchain/build.sh --clean
```

## Testing

Run all stateless tests:

```bash
./toolchain/test.sh
```

Run specific test:

```bash
./toolchain/test.sh --test 00001
```

Run integration tests:

```bash
./toolchain/test.sh --suite integration --test keeper
```
