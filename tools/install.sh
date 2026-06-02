#!/usr/bin/env bash
set -euo pipefail

CHANNEL="stable"
VERSION=""
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
REPO_BASE_URL="https://packages.clickhouse.com/tgz"
WORK_DIR=""
ARCH=""

usage()
{
    cat <<EOF
Usage: ./tools/install.sh [--version VERSION] [--channel stable|lts|testing]

Installs the ClickHouse static bundle for the current Linux architecture and links
`clickhouse`, `clickhouse-client`, `clickhouse-local`, and `clickhouse-server`
into ${INSTALL_DIR}.
EOF
}

die()
{
    echo "error: $*" >&2
    exit 1
}

need_cmd()
{
    command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

parse_args()
{
    while [[ $# -gt 0 ]]
    do
        case "$1" in
            --version)
                [[ $# -ge 2 ]] || die "--version requires a value"
                VERSION="$2"
                shift 2
                ;;
            --channel)
                [[ $# -ge 2 ]] || die "--channel requires a value"
                CHANNEL="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                die "unknown argument: $1"
                ;;
        esac
    done

    case "$CHANNEL" in
        stable|lts|testing)
            ;;
        *)
            die "unsupported channel: $CHANNEL"
            ;;
    esac
}

assert_linux()
{
    [[ "$(uname -s)" == "Linux" ]] || die "tools/install.sh currently supports Linux hosts"
}

normalize_arch()
{
    case "$(uname -m)" in
        x86_64|amd64)
            echo "amd64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        ppc64le)
            echo "ppc64le"
            ;;
        *)
            die "unsupported architecture: $(uname -m)"
            ;;
    esac
}

resolve_version()
{
    local index_url="$REPO_BASE_URL/$CHANNEL/"
    local version

    version="$({ curl -fsSL "$index_url" || true; } | grep -oE "clickhouse-common-static-[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+-$ARCH\.tgz" | sed -E "s/clickhouse-common-static-([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)-$ARCH\.tgz/\1/" | sort -V | tail -n 1)"

    [[ -n "$version" ]] || die "failed to resolve latest version for channel $CHANNEL and architecture $ARCH"
    printf '%s\n' "$version"
}

download_package()
{
    local archive_name="clickhouse-common-static-$VERSION-$ARCH.tgz"
    local archive_url="$REPO_BASE_URL/$CHANNEL/$archive_name"
    local archive_path="$WORK_DIR/$archive_name"

    echo "Downloading $archive_url" >&2
    curl -fsSL --retry 3 --output "$archive_path" "$archive_url"
    printf '%s\n' "$archive_path"
}

extract_package()
{
    local archive_path="$1"
    local package_dir

    tar -xzf "$archive_path" -C "$WORK_DIR"
    package_dir="$WORK_DIR/clickhouse-common-static-$VERSION"
    [[ -d "$package_dir" ]] || die "unexpected archive layout: $package_dir not found"
    printf '%s\n' "$package_dir"
}

install_binary_bundle()
{
    local package_dir="$1"
    local clickhouse_binary="$package_dir/usr/bin/clickhouse"
    local installer=()

    [[ -x "$clickhouse_binary" ]] || die "missing binary in archive: $clickhouse_binary"

    if [[ "$EUID" -ne 0 ]]
    then
        need_cmd sudo
        installer=(sudo)
    fi

    "${installer[@]}" install -d "$INSTALL_DIR"
    "${installer[@]}" install -m 0755 "$clickhouse_binary" "$INSTALL_DIR/clickhouse"
    "${installer[@]}" ln -sf "$INSTALL_DIR/clickhouse" "$INSTALL_DIR/clickhouse-client"
    "${installer[@]}" ln -sf "$INSTALL_DIR/clickhouse" "$INSTALL_DIR/clickhouse-local"
    "${installer[@]}" ln -sf "$INSTALL_DIR/clickhouse" "$INSTALL_DIR/clickhouse-server"
}

main()
{
    parse_args "$@"
    assert_linux
    need_cmd curl
    need_cmd grep
    need_cmd sed
    need_cmd sort
    need_cmd tail
    need_cmd tar
    need_cmd install
    need_cmd ln
    need_cmd mktemp

    ARCH="$(normalize_arch)"
    WORK_DIR="$(mktemp -d)"
    trap 'rm -rf "$WORK_DIR"' EXIT

    if [[ -z "$VERSION" ]]
    then
        VERSION="$(resolve_version)"
    fi

    local archive_path
    local package_dir
    archive_path="$(download_package)"
    package_dir="$(extract_package "$archive_path")"
    install_binary_bundle "$package_dir"

    echo "Installed ClickHouse $VERSION from channel $CHANNEL into $INSTALL_DIR"
    "$INSTALL_DIR/clickhouse" local --version
}

main "$@"
