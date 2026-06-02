#!/bin/bash
# tools/install.sh

set -e

VERSION="latest"
CHANNEL="stable"

usage() {
    echo "Usage: $0 [--version <version>] [--channel <stable|lts|testing>]"
    exit 1
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --version) 
            VERSION="$2"
            shift 
            ;;
        --channel) 
            CHANNEL="$2"
            if [[ "$CHANNEL" != "stable" && "$CHANNEL" != "lts" && "$CHANNEL" != "testing" ]]; then
                echo "Error: Invalid channel '$CHANNEL'. Must be stable, lts, or testing."
                usage
            fi
            shift 
            ;;
        -h|--help)
            usage
            ;;
        *) 
            echo "Unknown parameter passed: $1"
            usage
            ;;
    esac
    shift
done

echo "Installing ClickHouse..."
echo "Version: $VERSION"
echo "Channel: $CHANNEL"

# Export variables so the underlying install script can pick them up
export CLICKHOUSE_VERSION="$VERSION"
export CLICKHOUSE_CHANNEL="$CHANNEL"

curl -sL https://clickhouse.com/ | sh

echo "ClickHouse installation completed."
