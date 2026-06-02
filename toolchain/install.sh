#!/usr/bin/env bash
#
# ClickHouse Installation Toolchain
# ==================================
# This script provides a unified installation interface for ClickHouse
# across different platforms and deployment scenarios.
#
# Usage:
#   ./install.sh [OPTIONS]
#
# Options:
#   --channel <stable|testing|lts|prestable>  Release channel (default: stable)
#   --version <VERSION>                       Specific version to install
#   --method <deb|rpm|tgz|binary|docker>      Installation method
#   --prefix <PATH>                           Installation prefix (default: /usr)
#   --dry-run                                 Show commands without executing
#   --help                                    Show this help message
#
# Examples:
#   ./install.sh                              # Install latest stable via auto-detect
#   ./install.sh --channel lts                # Install latest LTS release
#   ./install.sh --version 24.8.1.2742        # Install specific version
#   ./install.sh --method docker              # Install via Docker
#   ./install.sh --method tgz --prefix /opt   # Install tarball to /opt

set -euo pipefail

# ============================================================================
# Constants and Defaults
# ============================================================================

readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly CLICKHOUSE_REPO_URL="https://github.com/ClickHouse/ClickHouse"
readonly CLICKHOUSE_RELEASE_URL="https://api.github.com/repos/ClickHouse/ClickHouse/releases"

# Default values
CHANNEL="${CHANNEL:-stable}"
VERSION="${VERSION:-}"
METHOD="${METHOD:-auto}"
PREFIX="${PREFIX:-/usr}"
DRY_RUN="${DRY_RUN:-false}"
ARCHITECTURE="$(uname -m)"
OS_TYPE="$(uname -s)"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# ============================================================================
# Logging Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_dry_run() {
    echo -e "${YELLOW}[DRY-RUN]${NC} Would execute: $*"
}

# ============================================================================
# Helper Functions
# ============================================================================

show_help() {
    head -20 "$0" | tail -18 | sed 's/^# \?//'
    exit 0
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "$ID"
    elif [[ "$OS_TYPE" == "Darwin" ]]; then
        echo "macos"
    elif [[ "$OS_TYPE" == "FreeBSD" ]]; then
        echo "freebsd"
    else
        echo "unknown"
    fi
}

detect_package_manager() {
    local os="$1"
    case "$os" in
        ubuntu|debian)
            echo "apt"
            ;;
        centos|rhel|fedora|amzn|rocky|almalinux)
            echo "yum"
            ;;
        opensuse*|sles)
            echo "zypper"
            ;;
        arch)
            echo "pacman"
            ;;
        alpine)
            echo "apk"
            ;;
        macos)
            echo "brew"
            ;;
        *)
            echo "none"
            ;;
    esac
}

validate_version() {
    local version="$1"
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && \
       [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format: $version"
        log_error "Expected format: MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH.REVISION"
        return 1
    fi
    return 0
}

fetch_latest_version() {
    local channel="$1"
    local url="${CLICKHOUSE_RELEASE_URL}/latest"
    
    case "$channel" in
        stable)
            url="${CLICKHOUSE_RELEASE_URL}/latest"
            ;;
        lts)
            url="${CLICKHOUSE_RELEASE_URL}/tags/v24.8-lts"
            ;;
        testing|prestable)
            url="${CLICKHOUSE_RELEASE_URL}"
            ;;
        *)
            log_error "Unknown channel: $channel"
            return 1
            ;;
    esac

    if command -v curl &>/dev/null; then
        curl -s "$url" | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4 | sed 's/^v//'
    elif command -v wget &>/dev/null; then
        wget -qO- "$url" | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4 | sed 's/^v//'
    else
        log_error "Neither curl nor wget found. Please install one of them."
        return 1
    fi
}

run_cmd() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "$@"
    else
        "$@"
    fi
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_warn "This script may require root privileges for system-wide installation."
        log_warn "Consider using --prefix to install to a user-writable directory."
    fi
}

# ============================================================================
# Installation Methods
# ============================================================================

install_via_apt() {
    local version="$1"
    log_info "Installing ClickHouse via APT..."
    
    run_cmd curl -fsSL https://packages.clickhouse.com/rpm/lts/CLICKHOUSE-KEY.GPG | \
        run_cmd gpg --dearmor -o /usr/share/keyrings/clickhouse-keyring.gpg
    
    run_cmd echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg] https://packages.clickhouse.com/deb stable main" > \
        /etc/apt/sources.list.d/clickhouse.list
    
    run_cmd apt-get update
    if [[ -n "$version" ]]; then
        run_cmd apt-get install -y "clickhouse-server=$version" "clickhouse-client=$version"
    else
        run_cmd apt-get install -y clickhouse-server clickhouse-client
    fi
    
    log_success "ClickHouse installed successfully via APT"
}

install_via_yum() {
    local version="$1"
    log_info "Installing ClickHouse via YUM..."
    
    run_cmd yum install -y yum-utils
    run_cmd yum-config-manager --add-repo https://packages.clickhouse.com/rpm/stable/clickhouse.repo
    
    if [[ -n "$version" ]]; then
        run_cmd yum install -y "clickhouse-server-$version" "clickhouse-client-$version"
    else
        run_cmd yum install -y clickhouse-server clickhouse-client
    fi
    
    log_success "ClickHouse installed successfully via YUM"
}

install_via_tgz() {
    local version="$1"
    local install_dir="${PREFIX}/clickhouse"
    
    log_info "Installing ClickHouse via tarball to $install_dir..."
    
    local arch="$ARCHITECTURE"
    [[ "$arch" == "x86_64" ]] && arch="amd64"
    [[ "$arch" == "aarch64" ]] && arch="arm64"
    
    local filename="clickhouse-${version:-latest}-${arch}.tgz"
    local download_url="https://packages.clickhouse.com/tgz/stable/$filename"
    
    log_info "Downloading $filename..."
    run_cmd curl -fsSL "$download_url" -o "/tmp/$filename"
    
    run_cmd mkdir -p "$install_dir"
    run_cmd tar -xzf "/tmp/$filename" -C "$install_dir"
    run_cmd rm -f "/tmp/$filename"
    
    # Create symlinks
    run_cmd ln -sf "$install_dir/clickhouse" "${PREFIX}/bin/clickhouse" 2>/dev/null || true
    run_cmd ln -sf "$install_dir/clickhouse-server" "${PREFIX}/bin/clickhouse-server" 2>/dev/null || true
    run_cmd ln -sf "$install_dir/clickhouse-client" "${PREFIX}/bin/clickhouse-client" 2>/dev/null || true
    
    log_success "ClickHouse installed successfully via tarball"
    log_info "Binaries are located in: $install_dir"
}

install_via_binary() {
    local version="$1"
    local install_dir="${PREFIX}/bin"
    
    log_info "Installing ClickHouse standalone binary..."
    
    local arch="$ARCHITECTURE"
    [[ "$arch" == "x86_64" ]] && arch="amd64"
    [[ "$arch" == "aarch64" ]] && arch="arm64"
    
    run_cmd mkdir -p "$install_dir"
    run_cmd curl -fsSL "https://packages.clickhouse.com/tgz/stable/clickhouse-${version:-latest}-${arch}.tgz" | \
        run_cmd tar -xzf - -C "$install_dir"
    
    log_success "ClickHouse binary installed to $install_dir"
}

install_via_docker() {
    local version="$1"
    local image="clickhouse/clickhouse-server${version:+:$version}"
    
    log_info "Setting up ClickHouse Docker container..."
    
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        return 1
    fi
    
    run_cmd docker pull "$image"
    run_cmd docker run -d \
        --name clickhouse-server \
        --ulimit nofile=262144:262144 \
        -p 8123:8123 \
        -p 9000:9000 \
        -v /tmp/clickhouse:/var/lib/clickhouse \
        "$image"
    
    log_success "ClickHouse Docker container started successfully"
    log_info "HTTP interface: http://localhost:8123"
    log_info "Native interface: localhost:9000"
}

install_via_brew() {
    log_info "Installing ClickHouse via Homebrew..."
    
    if ! command -v brew &>/dev/null; then
        log_error "Homebrew is not installed. Visit https://brew.sh to install it."
        return 1
    fi
    
    run_cmd brew install clickhouse
    log_success "ClickHouse installed successfully via Homebrew"
}

# ============================================================================
# Main Installation Logic
# ============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --channel)
                CHANNEL="$2"
                shift 2
                ;;
            --version)
                VERSION="$2"
                shift 2
                ;;
            --method)
                METHOD="$2"
                shift 2
                ;;
            --prefix)
                PREFIX="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help|-h)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done

    # Validate inputs
    if [[ -n "$VERSION" ]]; then
        validate_version "$VERSION" || exit 1
    fi

    # Auto-detect installation method if not specified
    if [[ "$METHOD" == "auto" ]]; then
        local os
        os="$(detect_os)"
        METHOD="$(detect_package_manager "$os")"
        
        if [[ "$METHOD" == "none" ]]; then
            log_info "No package manager detected, falling back to tarball installation"
            METHOD="tgz"
        fi
        
        log_info "Auto-detected installation method: $METHOD (OS: $os)"
    fi

    # Fetch version if not specified
    if [[ -z "$VERSION" ]]; then
        log_info "Fetching latest version for channel: $CHANNEL..."
        VERSION="$(fetch_latest_version "$CHANNEL")"
        log_info "Latest version: $VERSION"
    fi

    # Check privileges for system installations
    if [[ "$METHOD" != "docker" ]] && [[ "$PREFIX" == "/usr" ]]; then
        check_root
    fi

    # Execute installation
    log_info "Starting ClickHouse installation..."
    log_info "Channel: $CHANNEL | Version: $VERSION | Method: $METHOD | Prefix: $PREFIX"
    echo ""

    case "$METHOD" in
        apt)
            install_via_apt "$VERSION"
            ;;
        yum)
            install_via_yum "$VERSION"
            ;;
        tgz)
            install_via_tgz "$VERSION"
            ;;
        binary)
            install_via_binary "$VERSION"
            ;;
        docker)
            install_via_docker "$VERSION"
            ;;
        brew)
            install_via_brew "$VERSION"
            ;;
        *)
            log_error "Unsupported installation method: $METHOD"
            exit 1
            ;;
    esac

    echo ""
    log_success "Installation complete!"
    log_info "Run 'clickhouse-server' to start the server"
    log_info "Run 'clickhouse-client' to connect to the server"
}

# Run main function
main "$@"
