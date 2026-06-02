#!/usr/bin/env bash
# ClickHouse Installation Toolchain Script
# This script separates the installation logic from documentation.
# Usage: ./install.sh [options]
# Options:
#   --version <ver>   Install a specific version of ClickHouse
#   --dir <path>      Target directory for installation

set -euo pipefail

CLICKHOUSE_VERSION="latest"
INSTALL_DIR="/usr/bin"

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --version) CLICKHOUSE_VERSION="$2"; shift ;;
        --dir) INSTALL_DIR="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "Starting ClickHouse installation (Version: ${CLICKHOUSE_VERSION})..."

# Function to detect OS and Architecture
detect_env() {
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    if [[ "$ARCH" == "x86_64" ]]; then
        ARCH="amd64"
    elif [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
        ARCH="arm64"
    else
        echo "Unsupported architecture: $ARCH"
        exit 1
    fi
    echo "Detected environment: $OS $ARCH"
}

# Function to download ClickHouse binary
download_binary() {
    local url="https://builds.clickhouse.com/master/${ARCH}/clickhouse"
    if [[ "${CLICKHOUSE_VERSION}" != "latest" ]]; then
        url="https://builds.clickhouse.com/tags/v${CLICKHOUSE_VERSION}/${ARCH}/clickhouse"
    fi
    
    echo "Downloading from $url..."
    curl -fL "$url" -o "clickhouse"
    chmod +x clickhouse
}

# Function to install and setup
install_clickhouse() {
    echo "Installing to ${INSTALL_DIR}..."
    sudo mv clickhouse "${INSTALL_DIR}/clickhouse"
    
    echo "Setting up symbolic links..."
    sudo ln -sf "${INSTALL_DIR}/clickhouse" "${INSTALL_DIR}/clickhouse-server"
    sudo ln -sf "${INSTALL_DIR}/clickhouse" "${INSTALL_DIR}/clickhouse-client"
    sudo ln -sf "${INSTALL_DIR}/clickhouse" "${INSTALL_DIR}/clickhouse-local"

    echo "ClickHouse installed successfully."
    echo "Run 'clickhouse-server start' to begin."
}

detect_env
download_binary
install_clickhouse
