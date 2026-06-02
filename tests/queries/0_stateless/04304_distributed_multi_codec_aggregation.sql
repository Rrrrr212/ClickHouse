-- Tags: distributed, no-fasttest, no-parallel
--
-- Regression test for distributed aggregation + multi-codec partial column read.
-- Covers the gap where distributed aggregation only reads a subset of columns
-- that use different compression codecs (GCD, T64, ZSTD, Gorilla).
--
-- The bug scenario: when the remote shard decompresses only the columns
-- needed for aggregation, a codec chain mismatch or decompression buffer
-- reuse issue could corrupt data silently.
--
-- This test creates a table with 10+ columns using various codecs, then
-- runs distributed aggregations that touch different column subsets to
-- verify each codec decompresses correctly in isolation.

DROP TABLE IF EXISTS dist_multi_codec_agg;
DROP TABLE IF EXISTS local_multi_codec_agg;

CREATE TABLE local_multi_codec_agg
(
    key UInt64,
    -- Group 1: integer codecs
    gcd_u32 UInt32 CODEC(GCD, LZ4),
    gcd_u64 UInt64 CODEC(GCD, LZ4),
    dd_col Int64 CODEC(DoubleDelta, T64, ZSTD),
    t64_only Int32 CODEC(T64, LZ4),
    -- Group 2: float codecs
    gorilla_f64 Float64 CODEC(Gorilla),
    gorilla_f32 Float32 CODEC(Gorilla),
    -- Group 3: string/text codecs
    str_lz4 String CODEC(LZ4),
    str_zstd String CODEC(ZSTD(3)),
    -- Group 4: no codec (baseline)
    plain_u32 UInt32,
    plain_u64 UInt64,
    -- Group 5: composite
    gcd_dd UInt64 CODEC(GCD, DoubleDelta, ZSTD)
)
ENGINE = MergeTree
ORDER BY key
SETTINGS
    min_bytes_for_wide_part = 0,
    min_rows_for_wide_part = 0;

-- Insert data with known patterns for each codec
INSERT INTO local_multi_codec_agg
SELECT
    number AS key,
    -- GCD columns: multiples of known divisors
    toUInt32(number * 3) AS gcd_u32,
    number * 5 AS gcd_u64,
    -- DoubleDelta: monotonically increasing
    toInt64(number * 100) AS dd_col,
    -- T64: small integers
    toInt32(number % 1000) AS t64_only,
    -- Gorilla: small float deltas
    number * 0.5 AS gorilla_f64,
    toFloat32(number * 0.25) AS gorilla_f32,
    -- Strings
    toString(number % 100) AS str_lz4,
    toString(number % 50) AS str_zstd,
    -- Plain
    toUInt32(number) AS plain_u32,
    number AS plain_u64,
    -- Composite: GCD + DoubleDelta (multiples of 11, monotonic)
    number * 11 AS gcd_dd
FROM numbers(30000);

OPTIMIZE TABLE local_multi_codec_agg FINAL;

CREATE TABLE dist_multi_codec_agg AS local_multi_codec_agg
ENGINE = Distributed(test_cluster_two_shards, currentDatabase(), local_multi_codec_agg);

-- Test 1: Aggregate only GCD columns (integer codec isolation)
SELECT '--- Test 1: GCD columns only ---';
SELECT
    count() AS cnt,
    sum(gcd_u32) AS gcd_u32_sum,
    sum(gcd_u64) AS gcd_u64_sum,
    gcd_u32_sum = toUInt64(3) * cnt * (cnt - 1) / 2 / cnt AS gcd_u32_ok,
    gcd_u64_sum = 5 * cnt * (cnt - 1) / 2 / cnt AS gcd_u64_ok
FROM dist_multi_codec_agg
SETTINGS prefer_localhost_replica = 0;

-- Test 2: Aggregate only float codec columns
SELECT '--- Test 2: Float codec columns only ---';
SELECT
    sum(gorilla_f64) AS f64_sum,
    sum(gorilla_f32) AS f32_sum,
    abs(f64_sum - 30000 * 29999 * 0.5 / 2) < 1.0 AS f64_ok,
    abs(f32_sum - 30000 * 29999 * 0.25 / 2) < 100.0 AS f32_ok
FROM dist_multi_codec_agg
SETTINGS prefer_localhost_replica = 0;

-- Test 3: Aggregate DoubleDelta + T64 columns
SELECT '--- Test 3: DoubleDelta + T64 columns ---';
SELECT
    sum(dd_col) AS dd_sum,
    dd_sum = toInt64(100) * 30000 * 29999 / 2 AS dd_ok,
    sum(t64_only) AS t64_sum
FROM dist_multi_codec_agg
SETTINGS prefer_localhost_replica = 0;

-- Test 4: Composite codec column (GCD + DoubleDelta + ZSTD)
SELECT '--- Test 4: Composite codec column ---';
SELECT
    sum(gcd_dd) AS composite_sum,
    composite_sum = 11 * 30000 * 29999 / 2 AS composite_ok
FROM dist_multi_codec_agg
SETTINGS prefer_localhost_replica = 0;

-- Test 5: Mixed codec aggregation (GCD + Gorilla + plain)
SELECT '--- Test 5: Mixed codec aggregation ---';
SELECT
    sum(gcd_u64 + plain_u64) AS mixed_int_sum,
    sum(gorilla_f64 + toFloat64(plain_u32)) AS mixed_float_sum
FROM dist_multi_codec_agg
SETTINGS prefer_localhost_replica = 0;

-- Test 6: GROUP BY on plain column, aggregate codec columns
SELECT '--- Test 6: GROUP BY plain, aggregate codec ---';
SELECT
    key % 1000 AS bucket,
    count() AS cnt,
    sum(gcd_u32) AS gcd_sum,
    sum(gorilla_f64) AS gorilla_sum
FROM dist_multi_codec_agg
GROUP BY bucket
ORDER BY bucket
LIMIT 5
SETTINGS prefer_localhost_replica = 0;

-- Test 7: HAVING filter on decompressed codec column
SELECT '--- Test 7: HAVING on codec column ---';
SELECT
    gcd_u64 % 5 = 0 AS divisible,
    count() AS cnt
FROM dist_multi_codec_agg
GROUP BY divisible
HAVING cnt > 10000
ORDER BY divisible
SETTINGS prefer_localhost_replica = 0;

-- Test 8: String codec columns in aggregation
SELECT '--- Test 8: String codec columns ---';
SELECT
    countDistinct(str_lz4) AS lz4_distinct,
    countDistinct(str_zstd) AS zstd_distinct
FROM dist_multi_codec_agg
SETTINGS prefer_localhost_replica = 0;

-- Test 9: All columns hash verification (full decompression check)
SELECT '--- Test 9: Full column hash ---';
SELECT groupBitXor(sipHash64(*)) AS hash
FROM dist_multi_codec_agg
SETTINGS prefer_localhost_replica = 0;

DROP TABLE dist_multi_codec_agg;
DROP TABLE local_multi_codec_agg;
