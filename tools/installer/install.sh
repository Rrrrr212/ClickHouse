#!/bin/bash
# ClickHouse Official Installer Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source configuration and utilities
source "${SCRIPT_DIR}/config.sh"
source "${SCRIPT_DIR}/detect.sh"

# Default values
VERSION="${DEFAULT_VERSION}"
COMPONENTS="${DEFAULT_COMPONENTS}"
DRY_RUN=false
FORCE=false

print_info() {
    echo -e "${COLOR_GREEN}[INFO]${COLOR_RESET} $1"
}

print_warn() {
    echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1"
}

print_error() {
    echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1"
}

usage() {
    cat <<EOF
ClickHouse Installer

Usage: $0 [OPTIONS]

Options:
    -v, --version VERSION     Install specific version (default: latest)
    -c, --components COMPONENTS
                              Comma-separated list of components (default: $DEFAULT_COMPONENTS)
    -f, --force               Force installation even if already installed
    -n, --dry-run             Show what would be done without actually installing
    -h, --help                Show this help message

Examples:
    $0
    $0 --version 26.5.1.882
    $0 --components server,client
EOF
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -c|--components)
                COMPONENTS="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                usage
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                ;;
        esac
    done
}

main() {
    parse_args "$@"
    
    local OS=$(detect_os)
    local ARCH=$(detect_arch)
    
    print_info "Detected system: $OS ($ARCH)"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "Dry run mode - no changes will be made"
        print_info "Would install ClickHouse $VERSION with components: $COMPONENTS"
        return 0
    fi
    
    # Proceed with installation based on OS
    case "$OS" in
        linux)
            local DISTRO=$(detect_linux_distro)
            print_info "Detected Linux distribution: $DISTRO"
            # Add platform-specific installation logic here
            ;;
        macos)
            print_info "Installing on macOS"
            # macOS installation logic
            ;;
        freebsd)
            print_info "Installing on FreeBSD"
            # FreeBSD installation logic
            ;;
        *)
            print_error "Unsupported operating system: $OS"
            exit 1
            ;;
    esac
    
    print_info "Installation complete!"
}

main "$@"
