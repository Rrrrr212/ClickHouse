#!/usr/bin/env bash
set -euo pipefail

# ClickHouse Installation Toolchain Script
# This script provides a standalone installation mechanism for ClickHouse
# that can be used independently of the curl-pipe-sh pattern.

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DEFAULT_PREFIX="/usr"
readonly DEFAULT_USER="clickhouse"
readonly DEFAULT_GROUP="clickhouse"
readonly DEFAULT_DATA_DIR="/var/lib/clickhouse"
readonly DEFAULT_LOG_DIR="/var/log/clickhouse-server"
readonly DEFAULT_CONFIG_DIR="/etc/clickhouse-server"

readonly CH_VERSION="${CH_VERSION:-latest}"
readonly CH_ARCH="${CH_ARCH:-amd64}"
readonly CH_OS="${CH_OS:-linux}"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    local missing=()

    for cmd in curl tar chown id systemctl; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing[*]}"
        exit 1
    fi

    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi

    log_info "All prerequisites satisfied"
}

download_binary() {
    local version="$1"
    local arch="$2"
    local os="$3"
    local dest="$4"

    local url="https://builds.clickhouse.com/${os}/${arch}/clickhouse-${version}-${arch}.tgz"

    log_info "Downloading ClickHouse ${version} for ${os}/${arch}..."
    log_info "URL: ${url}"

    curl -fsSL "${url}" -o "${dest}/clickhouse.tgz" || {
        log_error "Failed to download ClickHouse binary"
        exit 1
    }

    tar -xzf "${dest}/clickhouse.tgz" -C "${dest}" || {
        log_error "Failed to extract ClickHouse archive"
        exit 1
    }

    rm -f "${dest}/clickhouse.tgz"
    log_info "Download and extraction complete"
}

create_user_and_group() {
    local user="$1"
    local group="$2"

    if ! getent group "$group" >/dev/null; then
        log_info "Creating group: ${group}"
        groupadd --system "$group"
    else
        log_info "Group ${group} already exists"
    fi

    if ! getent passwd "$user" >/dev/null; then
        log_info "Creating user: ${user}"
        useradd --system --no-create-home --shell /bin/false \
            --gid "$group" "$user"
    else
        log_info "User ${user} already exists"
    fi
}

create_directories() {
    log_info "Creating directories..."

    mkdir -p "${DEFAULT_CONFIG_DIR}/conf.d"
    mkdir -p "${DEFAULT_CONFIG_DIR}/users.d"
    mkdir -p "${DEFAULT_DATA_DIR}"
    mkdir -p "${DEFAULT_LOG_DIR}"

    chown -R "${DEFAULT_USER}:${DEFAULT_GROUP}" "${DEFAULT_DATA_DIR}"
    chown -R "${DEFAULT_USER}:${DEFAULT_GROUP}" "${DEFAULT_LOG_DIR}"
}

install_binaries() {
    local prefix="$1"
    local src="$2"

    log_info "Installing binaries to ${prefix}/bin..."

    mkdir -p "${prefix}/bin"

    cp "${src}/clickhouse" "${prefix}/bin/clickhouse"
    chmod 755 "${prefix}/bin/clickhouse"

    pushd "${prefix}/bin" >/dev/null
    for tool in clickhouse-server clickhouse-client clickhouse-local \
                clickhouse-benchmark clickhouse-keeper clickhouse-keeper-client \
                clickhouse-compressor clickhouse-obfuscator clickhouse-format \
                clickhouse-extract-from-config; do
        ln -sf clickhouse "$tool"
    done
    popd >/dev/null
}

install_service_systemd() {
    local service_file="/etc/systemd/system/clickhouse-server.service"

    log_info "Installing systemd service..."

    cat > "$service_file" << 'EOF'
[Unit]
Description=ClickHouse Server (Analytics DBMS)
Documentation=https://clickhouse.com/docs/
After=network.target

[Service]
Type=notify
User=clickhouse
Group=clickhouse
Restart=always
RestartSec=30
RuntimeDirectory=clickhouse-server
ExecStart=/usr/bin/clickhouse-server --config=/etc/clickhouse-server/config.xml --pid-file=/run/clickhouse-server/clickhouse-server.pid
LimitNOFILE=500000
LimitNPROC=500000
LimitCORE=infinity
CapabilityBoundingSet=CAP_NET_ADMIN CAP_IPC_LOCK CAP_SYS_NICE CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_IPC_LOCK CAP_SYS_NICE CAP_NET_BIND_SERVICE
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_info "Systemd service installed"
}

verify_installation() {
    log_info "Verifying installation..."

    local errors=0

    for binary in clickhouse clickhouse-server clickhouse-client; do
        if [[ -x "/usr/bin/${binary}" ]]; then
            log_info "  ✓ ${binary} is installed"
        else
            log_error "  ✗ ${binary} is missing"
            errors=$((errors + 1))
        fi
    done

    for dir in "${DEFAULT_CONFIG_DIR}" "${DEFAULT_DATA_DIR}" "${DEFAULT_LOG_DIR}"; do
        if [[ -d "$dir" ]]; then
            log_info "  ✓ Directory ${dir} exists"
        else
            log_error "  ✗ Directory ${dir} is missing"
            errors=$((errors + 1))
        fi
    done

    if [[ $errors -eq 0 ]]; then
        log_info "Installation verification PASSED"
    else
        log_error "Installation verification FAILED (${errors} errors)"
        exit 1
    fi
}

print_post_install() {
    echo ""
    echo "============================================"
    echo "  ClickHouse Installation Complete!"
    echo "============================================"
    echo ""
    echo "  Start the server:"
    echo "    sudo systemctl start clickhouse-server"
    echo ""
    echo "  Connect with client:"
    echo "    clickhouse-client"
    echo ""
    echo "  Check server status:"
    echo "    sudo systemctl status clickhouse-server"
    echo ""
    echo "  Documentation: https://clickhouse.com/docs/"
    echo "============================================"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Install ClickHouse from pre-built binaries.

Options:
    --prefix PATH          Installation prefix (default: ${DEFAULT_PREFIX})
    --user USER            System user (default: ${DEFAULT_USER})
    --group GROUP          System group (default: ${DEFAULT_GROUP})
    --version VERSION      ClickHouse version (default: ${CH_VERSION})
    --arch ARCH            Architecture (default: ${CH_ARCH})
    --local FILE           Install from local binary file
    --no-systemd           Skip systemd service installation
    --dry-run              Show what would be done without doing it
    -h, --help             Show this help message

Environment variables:
    CH_VERSION             ClickHouse version to install
    CH_ARCH                Target architecture
    CH_OS                  Target OS

Examples:
    # Install latest version
    sudo $0

    # Install specific version
    sudo $0 --version 24.8.1.2684

    # Install from a local binary
    sudo $0 --local ./clickhouse
EOF
}

main() {
    local prefix="${DEFAULT_PREFIX}"
    local user="${DEFAULT_USER}"
    local group="${DEFAULT_GROUP}"
    local version="${CH_VERSION}"
    local arch="${CH_ARCH}"
    local local_file=""
    local skip_systemd=false
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --prefix) prefix="$2"; shift 2 ;;
            --user) user="$2"; shift 2 ;;
            --group) group="$2"; shift 2 ;;
            --version) version="$2"; shift 2 ;;
            --arch) arch="$2"; shift 2 ;;
            --local) local_file="$2"; shift 2 ;;
            --no-systemd) skip_systemd=true; shift ;;
            --dry-run) dry_run=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) log_error "Unknown option: $1"; usage; exit 1 ;;
        esac
    done

    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN: Would install ClickHouse ${version} for ${arch} to ${prefix}"
        exit 0
    fi

    check_prerequisites

    local tmpdir
    tmpdir="$(mktemp -d "/tmp/clickhouse-install.XXXXXXXX")"
    trap 'rm -rf "$tmpdir"' EXIT

    if [[ -n "$local_file" ]]; then
        log_info "Using local binary: ${local_file}"
        cp "$local_file" "${tmpdir}/clickhouse"
    else
        download_binary "$version" "$arch" "$CH_OS" "$tmpdir"
    fi

    create_user_and_group "$user" "$group"
    create_directories
    install_binaries "$prefix" "$tmpdir"

    if [[ "$skip_systemd" != "true" ]]; then
        install_service_systemd
    fi

    verify_installation
    print_post_install
}

main "$@"