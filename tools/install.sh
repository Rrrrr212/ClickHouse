#!/bin/sh

set -e

# ClickHouse Modular Install Script
# Supports --version and --channel parameters for flexible installation.
#
# Usage:
#   ./install.sh                           # latest stable, default
#   ./install.sh --channel stable           # latest stable
#   ./install.sh --channel lts              # latest LTS
#   ./install.sh --channel testing          # latest testing/master
#   ./install.sh --version 26.5             # specific stable version
#   ./install.sh --version 26.3 --channel lts  # specific LTS version
#   CLICKHOUSE_ONLY=1 ./install.sh          # skip clickhousectl installation

CHANNEL="stable"
SPECIFIC_VERSION=""
CLICKHOUSE_ONLY="${CLICKHOUSE_ONLY:-}"

usage()
{
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --channel CHANNEL    Release channel: stable, lts, or testing (default: stable)
  --version VERSION    Install a specific version (e.g. 26.5, 26.3.8.23-lts)
                       When omitted, the latest version from the channel is used.
  --help               Show this help message

Environment:
  CLICKHOUSE_ONLY=1    Skip clickhousectl installation

Examples:
  $0                                    # latest stable
  $0 --channel lts                      # latest LTS
  $0 --channel testing                  # latest testing build
  $0 --version 26.5                     # specific stable version
  $0 --version 26.3.8.23-lts --channel lts  # specific LTS version
EOF
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --channel)
            if [ -z "$2" ]; then
                echo "Error: --channel requires a value (stable, lts, or testing)"
                exit 1
            fi
            CHANNEL="$2"
            shift 2
            ;;
        --version)
            if [ -z "$2" ]; then
                echo "Error: --version requires a value"
                exit 1
            fi
            SPECIFIC_VERSION="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

case "$CHANNEL" in
    stable|lts|testing)
        ;;
    *)
        echo "Error: invalid channel '$CHANNEL'. Must be one of: stable, lts, testing"
        exit 1
        ;;
esac

get_download_base_url()
{
    _channel="$1"
    _version="$2"

    if [ -n "$_version" ]; then
        echo "https://builds.clickhouse.com/${_channel}/${_version}/"
    else
        echo "https://builds.clickhouse.com/${_channel}/"
    fi
}

detect_platform_dir()
{
    _os=$(uname -s)
    _arch=$(uname -m)

    if [ "$_os" = "Linux" ]; then
        if [ "$_arch" = "x86_64" ] || [ "$_arch" = "amd64" ]; then
            HAS_SSE42=$(grep sse4_2 /proc/cpuinfo 2>/dev/null || true)
            if [ -n "$HAS_SSE42" ]; then
                if ldd --version 2>&1 | grep -q musl; then
                    echo "amd64musl"
                else
                    echo "amd64"
                fi
            else
                echo "amd64compat"
            fi
        elif [ "$_arch" = "aarch64" ] || [ "$_arch" = "arm64" ]; then
            HAS_ARMV82=$(grep -m 1 'Features' /proc/cpuinfo 2>/dev/null | awk '/asimd/ && /sha1/ && /aes/ && /atomics/ && /lrcpc/' || true)
            if [ -n "$HAS_ARMV82" ]; then
                echo "aarch64"
            else
                echo "aarch64v80compat"
            fi
        elif [ "$_arch" = "powerpc64le" ] || [ "$_arch" = "ppc64le" ]; then
            echo "powerpc64le"
        elif [ "$_arch" = "riscv64" ]; then
            echo "riscv64"
        elif [ "$_arch" = "s390x" ]; then
            echo "s390x"
        else
            echo ""
        fi
    elif [ "$_os" = "FreeBSD" ]; then
        if [ "$_arch" = "x86_64" ] || [ "$_arch" = "amd64" ]; then
            echo "freebsd"
        else
            echo ""
        fi
    elif [ "$_os" = "Darwin" ]; then
        if [ "$_arch" = "x86_64" ] || [ "$_arch" = "amd64" ]; then
            echo "macos"
        elif [ "$_arch" = "aarch64" ] || [ "$_arch" = "arm64" ]; then
            echo "macos-aarch64"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

install_clickhouse()
{
    _dir="$1"
    _base_url="$2"

    clickhouse_download_filename_prefix="clickhouse"
    clickhouse="$clickhouse_download_filename_prefix"

    if [ -f "$clickhouse" ]; then
        printf "ClickHouse binary %s already exists. Overwrite? [y/N] " "$clickhouse"
        read -r answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            rm -f "$clickhouse"
        else
            i=0
            while [ -f "$clickhouse" ]; do
                clickhouse="${clickhouse_download_filename_prefix}.${i}"
                i=$((i + 1))
            done
        fi
    fi

    URL="${_base_url}${_dir}/clickhouse"
    echo
    echo "Will download ${URL} into ${clickhouse}"
    echo
    curl -fL "${URL}" -o "${clickhouse}" && chmod a+x "${clickhouse}" || exit 1
    echo
    echo "Successfully downloaded the ClickHouse binary, you can run it as:"
    echo "    ./${clickhouse}"
    echo
    echo "You can also install it:"
    echo "sudo ./${clickhouse} install"
}

install_clickhousectl()
{
    if [ -n "${CLICKHOUSE_ONLY}" ]; then
        return 0
    fi

    _os=$(uname -s)
    _arch=$(uname -m)

    chctl_target=""
    if [ "$_os" = "Linux" ]; then
        if [ "$_arch" = "x86_64" ] || [ "$_arch" = "amd64" ]; then
            chctl_target="x86_64-unknown-linux-musl"
        elif [ "$_arch" = "aarch64" ] || [ "$_arch" = "arm64" ]; then
            chctl_target="aarch64-unknown-linux-musl"
        fi
    elif [ "$_os" = "Darwin" ]; then
        if [ "$_arch" = "x86_64" ] || [ "$_arch" = "amd64" ]; then
            chctl_target="x86_64-apple-darwin"
        elif [ "$_arch" = "aarch64" ] || [ "$_arch" = "arm64" ]; then
            chctl_target="aarch64-apple-darwin"
        fi
    fi

    if [ -z "${chctl_target}" ]; then
        echo "Skipping clickhousectl: unsupported platform for clickhousectl"
        return 0
    fi

    echo
    echo "Fetching the latest clickhousectl release..."
    chctl_tag=$(curl -fsSL "https://api.github.com/repos/ClickHouse/clickhousectl/releases/latest" \
        | grep '"tag_name"' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')

    if [ -z "${chctl_tag}" ]; then
        echo "Warning: could not determine the latest clickhousectl release. Continuing."
        return 0
    fi

    chctl_install_dir="${HOME}/.local/bin"
    chctl_archive="clickhousectl-${chctl_target}-${chctl_tag}.tar.gz"
    chctl_url="https://builds.clickhouse.com/clickhousectl/${chctl_archive}"
    echo "Will download ${chctl_url} into ${chctl_install_dir}/clickhousectl"

    chctl_tmp=$(mktemp -d)
    if mkdir -p "${chctl_install_dir}" \
        && curl -fsSL "${chctl_url}" -o "${chctl_tmp}/${chctl_archive}" \
        && tar -xzf "${chctl_tmp}/${chctl_archive}" -C "${chctl_tmp}" \
        && mv -f "${chctl_tmp}/clickhousectl-${chctl_target}-${chctl_tag}/clickhousectl" "${chctl_install_dir}/clickhousectl"
    then
        chmod a+x "${chctl_install_dir}/clickhousectl"
        ln -sf "${chctl_install_dir}/clickhousectl" "${chctl_install_dir}/chctl"
        echo
        echo "Successfully installed clickhousectl to ${chctl_install_dir}/clickhousectl"
        echo "Created alias: chctl -> clickhousectl"
        case ":$PATH:" in
            *":${chctl_install_dir}:"*) ;;
            *)
                echo
                echo "NOTE: ${chctl_install_dir} is not in your PATH."
                echo "Add it by running:"
                echo
                echo "  export PATH=\"${chctl_install_dir}:\$PATH\""
                echo
                echo "You may want to add that line to your shell profile (~/.bashrc, ~/.zshrc, etc.)"
                ;;
        esac
    else
        echo "Warning: failed to download clickhousectl. Continuing."
    fi
    rm -rf "${chctl_tmp}"
}

echo "ClickHouse Install Script"
echo "  Channel: ${CHANNEL}"
if [ -n "${SPECIFIC_VERSION}" ]; then
    echo "  Version: ${SPECIFIC_VERSION}"
else
    echo "  Version: latest"
fi
echo

DIR=$(detect_platform_dir)

if [ -z "${DIR}" ]; then
    echo "Operating system '$(uname -s)' / architecture '$(uname -m)' is unsupported."
    exit 1
fi

BASE_URL=$(get_download_base_url "${CHANNEL}" "${SPECIFIC_VERSION}")

install_clickhouse "${DIR}" "${BASE_URL}"
install_clickhousectl

echo
echo "Installation complete."