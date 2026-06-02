#!/bin/bash

set -euo pipefail

DEFAULT_CHANNEL="stable"
BASE_URL="https://packages.clickhouse.com"

usage() {
    cat <<EOF
ClickHouse Installation Script

Usage: $0 [OPTIONS]

Options:
  --version VERSION  Specify version to install (e.g., 24.8.1.2318)
  --channel CHANNEL  Specify channel (stable/lts/testing) [default: $DEFAULT_CHANNEL]
  --help, -h         Show this help message and exit

Example:
  $0 --channel testing
  $0 --version 24.8.1.2318
EOF
    exit 0
}

parse_args() {
    VERSION=""
    CHANNEL="$DEFAULT_CHANNEL"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --version)
                VERSION="$2"
                shift 2
                ;;
            --channel)
                CHANNEL="$2"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                echo "Error: Unknown option $1" >&2
                usage
                ;;
        esac
    done

    if [[ ! "$CHANNEL" =~ ^(stable|lts|testing)$ ]]; then
        echo "Error: Invalid channel $CHANNEL. Must be stable, lts, or testing." >&2
        usage
    fi
}

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "freebsd"* ]]; then
        echo "freebsd"
    else
        echo "unknown"
    fi
}

detect_arch() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64|amd64)
            echo "amd64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        *)
            echo "$arch"
            ;;
    esac
}

install_linux() {
    local channel="$1"
    local version="$2"
    local arch
    arch=$(detect_arch)

    echo "Installing ClickHouse on Linux (${arch}) from ${channel} channel..."

    if command -v apt-get &> /dev/null; then
        install_deb "$channel" "$version" "$arch"
    elif command -v yum &> /dev/null || command -v dnf &> /dev/null; then
        install_rpm "$channel" "$version" "$arch"
    else
        echo "Error: Unsupported package manager. Please install manually." >&2
        exit 1
    fi
}

install_deb() {
    local channel="$1"
    local version="$2"
    local arch="$3"

    apt-get update -qq
    apt-get install -y -qq apt-transport-https ca-certificates dirmngr
    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 8919F6BD2B48D754

    echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg] ${BASE_URL}/deb/${channel}/ stable main" | tee /etc/apt/sources.list.d/clickhouse.list
    mkdir -p /usr/share/keyrings
    gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv 8919F6BD2B48D754 --export --output /usr/share/keyrings/clickhouse-keyring.gpg

    apt-get update -qq

    if [[ -n "$version" ]]; then
        apt-get install -y clickhouse-server="$version" clickhouse-client="$version"
    else
        apt-get install -y clickhouse-server clickhouse-client
    fi

    echo "ClickHouse installed successfully!"
}

install_rpm() {
    local channel="$1"
    local version="$2"
    local arch="$3"

    local yum_cmd
    if command -v dnf &> /dev/null; then
        yum_cmd="dnf"
    else
        yum_cmd="yum"
    fi

    "$yum_cmd" install -y -q yum-utils
    rpm --import "${BASE_URL}/CLICKHOUSE-KEY.GPG"
    yum-config-manager --add-repo "${BASE_URL}/rpm/${channel}/x86_64"

    if [[ -n "$version" ]]; then
        "$yum_cmd" install -y "clickhouse-server-${version}" "clickhouse-client-${version}"
    else
        "$yum_cmd" install -y clickhouse-server clickhouse-client
    fi

    echo "ClickHouse installed successfully!"
}

install_macos() {
    local channel="$1"
    local version="$2"

    echo "Installing ClickHouse on macOS from ${channel} channel..."

    if [[ "$channel" == "testing" ]]; then
        echo "Warning: Testing channel not available for macOS via brew, using stable instead."
    fi

    if command -v brew &> /dev/null; then
        brew install clickhouse/clickhouse/clickhouse
    else
        echo "Error: Homebrew not found. Please install Homebrew first." >&2
        exit 1
    fi

    echo "ClickHouse installed successfully!"
}

install_freebsd() {
    local channel="$1"
    local version="$2"

    echo "Installing ClickHouse on FreeBSD from ${channel} channel..."

    if command -v pkg &> /dev/null; then
        pkg install -y clickhouse
    else
        echo "Error: pkg not found. Please install pkg first." >&2
        exit 1
    fi

    echo "ClickHouse installed successfully!"
}

main() {
    parse_args "$@"

    local os
    os=$(detect_os)

    case "$os" in
        linux)
            install_linux "$CHANNEL" "$VERSION"
            ;;
        macos)
            install_macos "$CHANNEL" "$VERSION"
            ;;
        freebsd)
            install_freebsd "$CHANNEL" "$VERSION"
            ;;
        *)
            echo "Error: Unsupported operating system $os" >&2
            exit 1
            ;;
    esac
}

main "$@"
