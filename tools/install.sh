#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_NAME=$(basename "$0")
readonly DEFAULT_CHANNEL="stable"
readonly DEFAULT_OUTPUT="clickhouse"
readonly DEFAULT_REPO="https://packages.clickhouse.com/tgz"

VERSION=""
CHANNEL="$DEFAULT_CHANNEL"
OUTPUT="$DEFAULT_OUTPUT"
INSTALL_DIR=""
TEMP_DIR=""

usage()
{
    cat <<EOF
Usage: $SCRIPT_NAME [--version VERSION] [--channel stable|lts|testing] [--output PATH] [--install-dir PATH]

Options:
  --version VERSION      Download a specific ClickHouse version.
  --channel CHANNEL      Release channel to use. Supported values: stable, lts, testing.
  --output PATH          Output path for the downloaded binary. Default: ./clickhouse
  --install-dir PATH     Copy the downloaded archive into this directory.
  -h, --help             Show this help message.
EOF
}

log()
{
    printf '%s\n' "$*"
}

fail()
{
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

cleanup()
{
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]
    then
        rm -rf "$TEMP_DIR"
    fi
}

require_command()
{
    command -v "$1" >/dev/null 2>&1 || fail "Required command '$1' is not available"
}

parse_args()
{
    while [ "$#" -gt 0 ]
    do
        case "$1" in
            --version)
                [ "$#" -ge 2 ] || fail "Missing value for --version"
                VERSION="$2"
                shift 2
                ;;
            --channel)
                [ "$#" -ge 2 ] || fail "Missing value for --channel"
                CHANNEL="$2"
                shift 2
                ;;
            --output)
                [ "$#" -ge 2 ] || fail "Missing value for --output"
                OUTPUT="$2"
                shift 2
                ;;
            --install-dir)
                [ "$#" -ge 2 ] || fail "Missing value for --install-dir"
                INSTALL_DIR="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                fail "Unknown argument: $1"
                ;;
        esac
    done
}

validate_channel()
{
    case "$CHANNEL" in
        stable|lts|testing)
            ;;
        *)
            fail "Unsupported channel '$CHANNEL'. Expected one of: stable, lts, testing"
            ;;
    esac
}

validate_os()
{
    local os
    os=$(uname -s)
    case "$os" in
        Linux)
            ;;
        *)
            fail "Unsupported operating system '$os'. This script currently supports Linux tgz packages."
            ;;
    esac
}

resolve_arch()
{
    local arch
    arch=$(uname -m)

    case "$arch" in
        x86_64|amd64)
            printf 'amd64'
            ;;
        aarch64|arm64)
            printf 'arm64'
            ;;
        *)
            fail "Unsupported architecture '$arch'. Supported values: x86_64/amd64, aarch64/arm64"
            ;;
    esac
}

resolve_version()
{
    if [ -n "$VERSION" ]
    then
        printf '%s' "$VERSION"
        return
    fi

    local listing_url version
    listing_url="$DEFAULT_REPO/$CHANNEL/"
    version=$(curl -fsSL "$listing_url" | grep -Eo 'clickhouse-common-static-[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+-(amd64|arm64)\.tgz' | sed -E 's/clickhouse-common-static-([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)-(amd64|arm64)\.tgz/\1/' | sort -V | tail -n 1)
    [ -n "$version" ] || fail "Unable to resolve the latest version for channel '$CHANNEL'"
    printf '%s' "$version"
}

ensure_output_path()
{
    local output_dir
    output_dir=$(dirname "$OUTPUT")
    mkdir -p "$output_dir"
}

create_temp_dir()
{
    local tmp_root
    tmp_root="${INSTALL_DIR:-$PWD}/tmp"
    mkdir -p "$tmp_root"
    TEMP_DIR=$(mktemp -d "$tmp_root/install.XXXXXX")
}

copy_archive_if_requested()
{
    local archive_path install_root
    archive_path="$1"
    if [ -n "$INSTALL_DIR" ]
    then
        install_root="$INSTALL_DIR"
        mkdir -p "$install_root"
        cp "$archive_path" "$install_root/"
    fi
}

download_binary()
{
    local version arch url archive_path extracted_binary output_basename
    version=$(resolve_version)
    arch=$(resolve_arch)
    url="$DEFAULT_REPO/$CHANNEL/clickhouse-common-static-$version-$arch.tgz"

    create_temp_dir
    archive_path="$TEMP_DIR/clickhouse-common-static.tgz"

    log "Downloading ClickHouse $version from channel '$CHANNEL'"
    log "Source archive: $url"

    curl -fsSL "$url" -o "$archive_path"
    tar -xzf "$archive_path" -C "$TEMP_DIR"

    extracted_binary="$TEMP_DIR/clickhouse-common-static-$version/usr/bin/clickhouse"
    [ -f "$extracted_binary" ] || fail "Downloaded archive does not contain the ClickHouse binary"

    ensure_output_path
    cp "$extracted_binary" "$OUTPUT"
    chmod +x "$OUTPUT"
    copy_archive_if_requested "$archive_path"

    output_basename=$(basename "$OUTPUT")
    log "Saved binary to $OUTPUT"
    log "Run './$output_basename local' or 'sudo $OUTPUT install' to continue"
}

main()
{
    trap cleanup EXIT
    require_command curl
    require_command tar
    parse_args "$@"
    validate_channel
    validate_os
    download_binary
}

main "$@"
