#!/bin/sh -e

set -e

PROGRAM_NAME="ClickHouse Installer"
DEFAULT_CHANNEL="stable"
VALID_CHANNELS="stable lts testing"

VERSION=""
CHANNEL="${DEFAULT_CHANNEL}"
INSTALL_DIR=""
SKIP_CHCTL=""
ONLY_BINARY=""
YES=""

usage()
{
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install ClickHouse binary for Linux, macOS, or FreeBSD.

Options:
  --version VERSION   Install a specific version (e.g. 24.8.4.13, 25.3)
                      If omitted, the latest version for the selected channel is installed.
  --channel CHANNEL   Release channel: stable, lts, testing
                      Default: ${DEFAULT_CHANNEL}
  --install-dir DIR   Directory to install the binary into (default: current directory)
  --skip-chctl        Skip clickhousectl installation
  --only-binary       Only download the clickhouse binary, skip clickhousectl
  -y, --yes           Answer yes to all prompts (non-interactive mode)
  -h, --help          Show this help message

Examples:
  $(basename "$0")                           # Latest stable
  $(basename "$0") --channel lts             # Latest LTS
  $(basename "$0") --channel testing         # Latest testing (master)
  $(basename "$0") --version 24.8.4.13       # Specific version (stable)
  $(basename "$0") --version 25.3 --channel lts  # Specific version from LTS channel
EOF
}

parse_args()
{
    while [ $# -gt 0 ]; do
        case "$1" in
            --version)
                if [ -z "$2" ] || echo "$2" | grep -q '^--'; then
                    echo "Error: --version requires a value" >&2
                    exit 1
                fi
                VERSION="$2"
                shift 2
                ;;
            --channel)
                if [ -z "$2" ] || echo "$2" | grep -q '^--'; then
                    echo "Error: --channel requires a value" >&2
                    exit 1
                fi
                CHANNEL="$2"
                shift 2
                ;;
            --install-dir)
                if [ -z "$2" ] || echo "$2" | grep -q '^--'; then
                    echo "Error: --install-dir requires a value" >&2
                    exit 1
                fi
                INSTALL_DIR="$2"
                shift 2
                ;;
            --skip-chctl)
                SKIP_CHCTL=1
                shift
                ;;
            --only-binary)
                ONLY_BINARY=1
                shift
                ;;
            -y|--yes)
                YES=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Error: Unknown option: $1" >&2
                usage >&2
                exit 1
                ;;
        esac
    done
}

validate_channel()
{
    for c in ${VALID_CHANNELS}; do
        if [ "${CHANNEL}" = "${c}" ]; then
            return 0
        fi
    done
    echo "Error: Invalid channel '${CHANNEL}'. Valid channels: ${VALID_CHANNELS}" >&2
    exit 1
}

detect_platform()
{
    OS=$(uname -s)
    ARCH=$(uname -m)
    DIR=

    if [ "${OS}" = "Linux" ]; then
        if [ "${ARCH}" = "x86_64" ] || [ "${ARCH}" = "amd64" ]; then
            HAS_SSE42=$(grep sse4_2 /proc/cpuinfo 2>/dev/null || true)
            if [ -n "${HAS_SSE42}" ]; then
                if ldd --version 2>&1 | grep -q musl; then
                    DIR="amd64musl"
                else
                    DIR="amd64"
                fi
            else
                DIR="amd64compat"
            fi
        elif [ "${ARCH}" = "aarch64" ] || [ "${ARCH}" = "arm64" ]; then
            HAS_ARMV82=$(grep -m 1 'Features' /proc/cpuinfo 2>/dev/null | awk '/asimd/ && /sha1/ && /aes/ && /atomics/ && /lrcpc/' || true)
            if [ -n "${HAS_ARMV82}" ]; then
                DIR="aarch64"
            else
                DIR="aarch64v80compat"
            fi
        elif [ "${ARCH}" = "powerpc64le" ] || [ "${ARCH}" = "ppc64le" ]; then
            DIR="powerpc64le"
        elif [ "${ARCH}" = "riscv64" ]; then
            DIR="riscv64"
        elif [ "${ARCH}" = "s390x" ]; then
            DIR="s390x"
        fi
    elif [ "${OS}" = "FreeBSD" ]; then
        if [ "${ARCH}" = "x86_64" ] || [ "${ARCH}" = "amd64" ]; then
            DIR="freebsd"
        fi
    elif [ "${OS}" = "Darwin" ]; then
        if [ "${ARCH}" = "x86_64" ] || [ "${ARCH}" = "amd64" ]; then
            DIR="macos"
        elif [ "${ARCH}" = "aarch64" ] || [ "${ARCH}" = "arm64" ]; then
            DIR="macos-aarch64"
        fi
    fi

    if [ -z "${DIR}" ]; then
        echo "Error: Operating system '${OS}' / architecture '${ARCH}' is unsupported." >&2
        exit 1
    fi
}

resolve_channel_path()
{
    case "${CHANNEL}" in
        stable)
            CHANNEL_PATH="stable"
            ;;
        lts)
            CHANNEL_PATH="lts"
            ;;
        testing)
            CHANNEL_PATH="master"
            ;;
        *)
            echo "Error: Unknown channel '${CHANNEL}'" >&2
            exit 1
            ;;
    esac
}

build_download_url()
{
    if [ -n "${VERSION}" ]; then
        URL="https://builds.clickhouse.com/${CHANNEL_PATH}/${VERSION}/${DIR}/clickhouse"
    else
        URL="https://builds.clickhouse.com/${CHANNEL_PATH}/${DIR}/clickhouse"
    fi
}

resolve_output_path()
{
    clickhouse_download_filename_prefix="clickhouse"
    clickhouse="${clickhouse_download_filename_prefix}"

    if [ -n "${INSTALL_DIR}" ]; then
        clickhouse="${INSTALL_DIR}/${clickhouse}"
        mkdir -p "${INSTALL_DIR}"
    fi

    if [ -f "${clickhouse}" ]; then
        if [ -n "${YES}" ]; then
            rm -f "${clickhouse}"
        else
            read -p "ClickHouse binary ${clickhouse} already exists. Overwrite? [y/N] " answer
            if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
                rm -f "${clickhouse}"
            else
                i=0
                while [ -f "${clickhouse}" ]; do
                    clickhouse="${INSTALL_DIR:-.}/${clickhouse_download_filename_prefix}.${i}"
                    i=$((i + 1))
                done
            fi
        fi
    fi
}

download_clickhouse()
{
    echo ""
    echo "Channel : ${CHANNEL}"
    if [ -n "${VERSION}" ]; then
        echo "Version : ${VERSION}"
    else
        echo "Version : latest"
    fi
    echo "Platform: ${OS} / ${ARCH} (${DIR})"
    echo ""
    echo "Will download ${URL} into ${clickhouse}"
    echo ""
    curl -fSL "${URL}" -o "${clickhouse}" && chmod a+x "${clickhouse}" || {
        echo "Error: Failed to download ClickHouse from ${URL}" >&2
        exit 1
    }
    echo ""
    echo "Successfully downloaded the ClickHouse binary, you can run it as:"
    echo "    ${clickhouse}"
    echo ""
    echo "You can also install it:"
    echo "    sudo ${clickhouse} install"
}

install_clickhousectl()
{
    if [ -n "${SKIP_CHCTL}" ] || [ -n "${ONLY_BINARY}" ]; then
        return 0
    fi

    chctl_target=
    if [ "${OS}" = "Linux" ]; then
        if [ "${ARCH}" = "x86_64" ] || [ "${ARCH}" = "amd64" ]; then
            chctl_target="x86_64-unknown-linux-musl"
        elif [ "${ARCH}" = "aarch64" ] || [ "${ARCH}" = "arm64" ]; then
            chctl_target="aarch64-unknown-linux-musl"
        fi
    elif [ "${OS}" = "Darwin" ]; then
        if [ "${ARCH}" = "x86_64" ] || [ "${ARCH}" = "amd64" ]; then
            chctl_target="x86_64-apple-darwin"
        elif [ "${ARCH}" = "aarch64" ] || [ "${ARCH}" = "arm64" ]; then
            chctl_target="aarch64-apple-darwin"
        fi
    fi

    if [ -z "${chctl_target}" ]; then
        return 0
    fi

    echo ""
    echo "Fetching the latest clickhousectl release..."
    chctl_tag=$(curl -fsSL "https://api.github.com/repos/ClickHouse/clickhousectl/releases/latest" \
        2>/dev/null | grep '"tag_name"' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/' || true)

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
        && mv -f "${chctl_tmp}/clickhousectl-${chctl_target}-${chctl_tag}/clickhousectl" "${chctl_install_dir}/clickhousectl"; then
        chmod a+x "${chctl_install_dir}/clickhousectl"
        ln -sf "${chctl_install_dir}/clickhousectl" "${chctl_install_dir}/chctl"
        echo ""
        echo "Successfully installed clickhousectl to ${chctl_install_dir}/clickhousectl"
        echo "Created alias: chctl -> clickhousectl"
        case ":$PATH:" in
            *":${chctl_install_dir}:"*) ;;
            *)
                echo ""
                echo "NOTE: ${chctl_install_dir} is not in your PATH."
                echo "Add it by running:"
                echo ""
                echo "  export PATH=\"${chctl_install_dir}:\$PATH\""
                echo ""
                echo "You may want to add that line to your shell profile (~/.bashrc, ~/.zshrc, etc.)"
                ;;
        esac
    else
        echo "Warning: failed to download clickhousectl. Continuing."
    fi
    rm -rf "${chctl_tmp}"
}

main()
{
    parse_args "$@"
    validate_channel
    detect_platform
    resolve_channel_path
    build_download_url
    resolve_output_path
    download_clickhouse
    install_clickhousectl
}

main "$@"
