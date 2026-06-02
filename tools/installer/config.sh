#!/bin/bash
# ClickHouse Installer Configuration

# Repository configuration
REPO_BASE_URL="https://packages.clickhouse.com"
DEB_REPO_URL="${REPO_BASE_URL}/deb/stable"
RPM_REPO_URL="${REPO_BASE_URL}/rpm/stable"
TAR_REPO_URL="${REPO_BASE_URL}/tgz"

# Package configuration
DEFAULT_COMPONENTS="clickhouse-server,clickhouse-client,clickhouse-common-static"
GPG_KEY_URL="https://packages.clickhouse.com/CLICKHOUSE-KEY.GPG"
GPG_KEY_ID="8919F6BD"

# Installation paths
PREFIX="/usr"
CONF_DIR="/etc/clickhouse-server"
DATA_DIR="/var/lib/clickhouse"
LOG_DIR="/var/log/clickhouse-server"

# Version configuration
DEFAULT_VERSION="latest"

# Color output
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RESET='\033[0m'
