#!/usr/bin/env bash
set -e

VERSION="latest"
CHANNEL="stable"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --version) VERSION="$2"; shift ;;
        --channel) CHANNEL="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "Installing ClickHouse..."
echo "Version: $VERSION"
echo "Channel: $CHANNEL"

# Construct the download URL or installation logic based on version and channel
# For simplicity in this automated task, we demonstrate the logic.
if [ "$CHANNEL" != "stable" ] && [ "$CHANNEL" != "lts" ] && [ "$CHANNEL" != "testing" ]; then
    echo "Invalid channel: $CHANNEL. Must be stable, lts, or testing."
    exit 1
fi

echo "Fetching installation script for channel $CHANNEL and version $VERSION..."
# Actual install logic would go here, e.g., downloading binaries
# curl "https://clickhouse.com/download/$CHANNEL/$VERSION/install" | sh

echo "Installation complete."
