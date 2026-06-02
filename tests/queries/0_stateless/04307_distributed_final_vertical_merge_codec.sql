-- Tags: no-fasttest
--
-- Regression test for distributed FINAL query + vertical merge + mixed codec layouts.
--
-- Covers the gap where:
--   1. A distributed query with FINAL triggers vertical merge on remote shards
--   2. Remote shards have parts with mixed compression layouts
--      (some with compress_per_column_in_compact_parts=true, some false)
--   3. Vertical merge must correctly handle codec chains during part merging
--
-- This test creates parts with different compression layouts, then runs
-- SELECT FINAL through a Distributed table to verify vertical merge
-- correctly handles codec chains across mixed-layout parts.

DROP TABLE IF EXISTS dist_final_vertical_codec_local;
DROP TABLE IF EXISTS dist_final_vertical_codec;

-- Create local table with vertical merge friendly settings
CREATE TABLE dist_final_vertical_codec_local
(
    id UInt64,
    -- Multiple columns to trigger vertical merge
    c1 UInt64 CODEC(GCD, LZ4),
    c2 Int64 CODEC(DoubleDelta, T64, ZSTD),
    c3 Float64 CODEC(Gorilla),
    c4 String CODEC(LZ4),
    c5 UInt32,
    c6 UInt32,
    c7 UInt32,
    c8 UInt32,
    c9 UInt32,
    c10 UInt32
)
ENGINE = MergeTree
ORDER BY id
SETTINGS
    min_bytes_for_wide_part = 0,
    min_rows_for_wide_part = 0,
    vertical_merge_algorithm_min_rows_to_activate = 0,
    vertical_merge_algorithm_min_columns_to_activate = 0,
    compress_per_column_in_compact_parts = true;

-- Insert first batch (compress_per_column = true layout)
INSERT INTO dist_final_vertical_codec_local
SELECT
    number,
    number * 3,
    toInt64(number * 100),
    number * 0.1,
    toString(number % 100),
    toUInt32(number),
    toUInt32(number),
    toUInt32(number),
    toUInt32(number),
    toUInt32(number),
    toUInt32(number)
FROM numbers(5000);

-- Change compression layout setting
ALTER TABLE dist_final_vertical_codec_local
MODIFY SETTING compress_per_column_in_compact_parts = false;

-- Insert second batch (compress_per_column = false layout)
INSERT INTO dist_final_vertical_codec_local
SELECT
    number + 5000,
    (number + 5000) * 3,
    toInt64((number + 5000) * 100),
    (number + 5000) * 0.1,
    toString((number + 5000) % 100),
    toUInt32(number + 5000),
    toUInt32(number + 5000),
    toUInt32(number + 5000),
    toUInt32(number + 5000),
    toUInt32(number + 5000),
    toUInt32(number + 5000)
FROM numbers(5000);

-- Create distributed table
CREATE TABLE dist_final_vertical_codec AS dist_final_vertical_codec_local
ENGINE = Distributed(test_cluster_two_shards, currentDatabase(), dist_final_vertical_codec_local);

-- Test 1: SELECT FINAL triggers vertical merge on remote
SELECT '--- Test 1: SELECT FINAL with mixed codec layouts ---';
SELECT
    count() AS cnt,
    sum(c1) AS c1_sum,
    sum(c2) AS c2_sum,
    countDistinct(c4) AS c4_distinct
FROM dist_final_vertical_codec FINAL
SETTINGS prefer_localhost_replica = 0;

-- Test 2: Verify data integrity after FINAL
SELECT '--- Test 2: Data integrity after FINAL ---';
SELECT
    cnt = 20000 AS count_ok,
    c1_sum = 3 * 10000 * 9999 / 2 AS c1_ok,
    c2_sum = toInt64(100) * 10000 * 9999 / 2 AS c2_ok
FROM
(
    SELECT
        count() AS cnt,
        sum(c1) AS c1_sum,
        sum(c2) AS c2_sum
    FROM dist_final_vertical_codec FINAL
);

-- Test 3: GROUP BY + FINAL on distributed
SELECT '--- Test 3: GROUP BY + FINAL ---';
SELECT
    id % 1000 AS bucket,
    count() AS cnt,
    sum(c1) AS c1_sum,
    avg(c3) AS c3_avg
FROM dist_final_vertical_codec FINAL
GROUP BY bucket
ORDER BY bucket
LIMIT 5
SETTINGS prefer_localhost_replica = 0;

-- Test 4: OPTIMIZE FINAL then verify
OPTIMIZE TABLE dist_final_vertical_codec_local FINAL;

SELECT '--- Test 4: Post-OPTIMIZE FINAL read ---';
SELECT
    count() AS cnt,
    sum(c1) AS c1_sum,
    min(c2) AS c2_min,
    max(c3) AS c3_max
FROM dist_final_vertical_codec
SETTINGS prefer_localhost_replica = 0;

-- Test 5: Partial column read after vertical merge
SELECT '--- Test 5: Partial column read post-merge ---';
SELECT
    sum(c1 + c5) AS partial_sum,
    sum(c3 + toFloat64(c6)) AS float_sum
FROM dist_final_vertical_codec FINAL
SETTINGS prefer_localhost_replica = 0;

DROP TABLE dist_final_vertical_codec;
DROP TABLE dist_final_vertical_codec_local;
