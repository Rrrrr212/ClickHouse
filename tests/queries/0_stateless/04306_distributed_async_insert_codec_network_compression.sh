#!/usr/bin/env bash
# Tags: no-fasttest, long
#
# Regression test for distributed async insert + per-column compression codec
# + network compression interaction.
#
# Covers the gap where:
#   1. Distributed async insert uses network_compression_method (zstd/lz4)
#   2. Target MergeTree table has per-column codecs (GCD, T64, Gorilla)
#   3. The interaction between network-level compression and column-level
#      codecs could cause data corruption during INSERT → SELECT round-trip
#
# This test verifies that data inserted through a Distributed table with
# network compression is correctly stored with column codecs and readable
# back with identical values.

CUR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$CUR_DIR"/_inc/double_quotes_limited.sh

$CLICKHOUSE_CLIENT --query "DROP TABLE IF EXISTS dist_async_codec_local"
$CLICKHOUSE_CLIENT --query "DROP TABLE IF EXISTS dist_async_codec"

$CLICKHOUSE_CLIENT --query "
CREATE TABLE dist_async_codec_local
(
    id UInt64,
    gcd_col UInt64 CODEC(GCD, LZ4),
    dd_col Int64 CODEC(DoubleDelta, T64, ZSTD),
    gorilla_col Float64 CODEC(Gorilla),
    str_col String CODEC(ZSTD(1))
)
ENGINE = MergeTree
ORDER BY id
SETTINGS
    min_bytes_for_wide_part = 0,
    min_rows_for_wide_part = 0
"

$CLICKHOUSE_CLIENT --query "
CREATE TABLE dist_async_codec AS dist_async_codec_local
ENGINE = Distributed(test_cluster_two_shards, currentDatabase(), dist_async_codec_local)
"

# Test 1: Async insert with ZSTD network compression
$CLICKHOUSE_CLIENT --query "
SET distributed_foreground_insert = 0, network_compression_method = 'zstd';
INSERT INTO dist_async_codec
SELECT
    number,
    number * 7,
    toInt64(number * 1000),
    number * 0.5,
    toString(number)
FROM numbers(10000)
"

# Wait for async insert to flush
sleep 2
$CLICKHOUSE_CLIENT --query "SYSTEM FLUSH DISTRIBUTED dist_async_codec"

# Verify data integrity
echo "--- Test 1: Async insert with ZSTD network compression ---"
$CLICKHOUSE_CLIENT --query "
SELECT
    count() AS cnt,
    sum(gcd_col) AS gcd_sum,
    gcd_sum = 7 * 10000 * 9999 / 2 AS gcd_ok,
    sum(dd_col) = toInt64(1000) * 10000 * 9999 / 2 AS dd_ok
FROM dist_async_codec
"

# Test 2: Async insert with LZ4 network compression
$CLICKHOUSE_CLIENT --query "DROP TABLE IF EXISTS dist_async_codec_local"
$CLICKHOUSE_CLIENT --query "DROP TABLE IF EXISTS dist_async_codec"

$CLICKHOUSE_CLIENT --query "
CREATE TABLE dist_async_codec_local
(
    id UInt64,
    gcd_col UInt64 CODEC(GCD, LZ4),
    gorilla_col Float64 CODEC(Gorilla)
)
ENGINE = MergeTree
ORDER BY id
SETTINGS
    min_bytes_for_wide_part = 0,
    min_rows_for_wide_part = 0
"

$CLICKHOUSE_CLIENT --query "
CREATE TABLE dist_async_codec AS dist_async_codec_local
ENGINE = Distributed(test_cluster_two_shards, currentDatabase(), dist_async_codec_local)
"

$CLICKHOUSE_CLIENT --query "
SET distributed_foreground_insert = 0, network_compression_method = 'lz4';
INSERT INTO dist_async_codec
SELECT
    number,
    number * 11,
    number * 0.25
FROM numbers(5000)
"

sleep 2
$CLICKHOUSE_CLIENT --query "SYSTEM FLUSH DISTRIBUTED dist_async_codec"

echo "--- Test 2: Async insert with LZ4 network compression ---"
$CLICKHOUSE_CLIENT --query "
SELECT
    count() AS cnt,
    sum(gcd_col) = 11 * 5000 * 4999 / 2 AS gcd_ok,
    abs(sum(gorilla_col) - 5000 * 4999 * 0.25 / 2) < 1.0 AS gorilla_ok
FROM dist_async_codec
"

# Test 3: Foreground insert (synchronous) with network compression
$CLICKHOUSE_CLIENT --query "
SET distributed_foreground_insert = 1, network_compression_method = 'zstd';
INSERT INTO dist_async_codec
SELECT
    number + 5000,
    (number + 5000) * 11,
    (number + 5000) * 0.25
FROM numbers(5000)
"

echo "--- Test 3: Foreground insert with ZSTD ---"
$CLICKHOUSE_CLIENT --query "
SELECT
    count() AS cnt,
    cnt = 10000 AS count_ok,
    sum(gcd_col) = 11 * (5000 * 4999 / 2 + 5000 * 5000 + 5000 * 4999 / 2) AS gcd_ok
FROM dist_async_codec
"

$CLICKHOUSE_CLIENT --query "DROP TABLE IF EXISTS dist_async_codec"
$CLICKHOUSE_CLIENT --query "DROP TABLE IF EXISTS dist_async_codec_local"
