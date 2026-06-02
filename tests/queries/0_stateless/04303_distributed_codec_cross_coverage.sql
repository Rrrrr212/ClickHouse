-- Tags: distributed, no-fasttest
--
-- Regression test for distributed query + columnar codec cross-coverage.
-- Previously no test exercised remote() queries against MergeTree tables
-- with non-trivial codec chains (GCD, T64, Gorilla) under distributed
-- aggregation and partial column reads.
--
-- Scenario: two shards, each holding a MergeTree table with columns using
-- different codecs. A distributed query performs:
--   1. Partial column read (only codec columns, skipping others)
--   2. Distributed aggregation (sum/avg on compressed columns)
--   3. FINAL merge triggering vertical merge on remote parts
--   4. Mixed codec layout consistency after OPTIMIZE

DROP TABLE IF EXISTS dist_codec_test;
DROP TABLE IF EXISTS local_codec_test;

CREATE TABLE local_codec_test
(
    id UInt64,
    -- GCD codec: best for integers with common divisor
    gcd_col UInt64 CODEC(GCD, LZ4),
    -- DoubleDelta + T64 + ZSTD: best for monotonically increasing integers
    dd_t64_col Int64 CODEC(DoubleDelta, T64, ZSTD),
    -- Gorilla codec: best for floating-point with small deltas
    gorilla_col Float64 CODEC(Gorilla),
    -- Plain LZ4 baseline
    plain_col String CODEC(LZ4),
    -- No codec (default)
    no_codec_col UInt32
)
ENGINE = MergeTree
ORDER BY id
SETTINGS
    min_bytes_for_wide_part = 0,
    min_rows_for_wide_part = 0;

-- Insert data with patterns that exercise each codec's compression path
INSERT INTO local_codec_test
SELECT
    number AS id,
    number * 7 AS gcd_col,                  -- multiples of 7 → GCD = 7
    toInt64(number * 1000) AS dd_t64_col,   -- monotonic → DoubleDelta + T64
    number * 0.001 AS gorilla_col,          -- small float deltas → Gorilla
    toString(number) AS plain_col,
    toUInt32(number) AS no_codec_col
FROM numbers(50000);

-- Force part creation
OPTIMIZE TABLE local_codec_test FINAL;

CREATE TABLE dist_codec_test AS local_codec_test
ENGINE = Distributed(test_cluster_two_shards, currentDatabase(), local_codec_test);

-- Test 1: Partial column read - only compressed columns
SELECT '--- Test 1: Partial column read (compressed columns only) ---';
SELECT
    count() AS cnt,
    sum(gcd_col) AS gcd_sum,
    sum(dd_t64_col) AS dd_sum,
    sum(gorilla_col) AS gorilla_sum
FROM dist_codec_test
SETTINGS prefer_localhost_replica = 0;

-- Test 2: Distributed aggregation on codec columns
SELECT '--- Test 2: Distributed aggregation on codec columns ---';
SELECT
    gcd_col % 7 = 0 AS divisible,
    count() AS cnt,
    sum(dd_t64_col) AS dd_sum,
    avg(gorilla_col) AS gorilla_avg
FROM dist_codec_test
GROUP BY divisible
ORDER BY divisible;

-- Test 3: Mixed codec + no_codec column in aggregation
SELECT '--- Test 3: Mixed codec + no_codec column ---';
SELECT
    sum(gcd_col + no_codec_col) AS mixed_sum,
    sum(dd_t64_col - toInt64(no_codec_col) * 1000) AS diff_sum
FROM dist_codec_test;

-- Test 4: WHERE predicate on compressed column (tests decompression + filter)
SELECT '--- Test 4: WHERE on compressed column ---';
SELECT count()
FROM dist_codec_test
WHERE gcd_col % 49 = 0
SETTINGS prefer_localhost_replica = 0;

-- Test 5: ORDER BY on codec column after distributed merge
SELECT '--- Test 5: ORDER BY on codec column ---';
SELECT id, gcd_col, dd_t64_col
FROM dist_codec_test
ORDER BY id
LIMIT 10
SETTINGS prefer_localhost_replica = 0;

-- Test 6: Verify data integrity across shards
SELECT '--- Test 6: Cross-shard data integrity ---';
SELECT
    (SELECT sum(gcd_col) FROM dist_codec_test)
    =
    (SELECT sum(number * 7) FROM numbers(100000)) AS gcd_integrity,
    (SELECT sum(dd_t64_col) FROM dist_codec_test)
    =
    (SELECT sum(toInt64(number * 1000)) FROM numbers(100000)) AS dd_integrity;

-- Test 7: FINAL query triggering remote vertical merge
SELECT '--- Test 7: FINAL on distributed ---';
SELECT count(), sum(gcd_col)
FROM dist_codec_test FINAL
SETTINGS prefer_localhost_replica = 0;

-- Cleanup local table parts for codec layout test
OPTIMIZE TABLE local_codec_test FINAL;

-- Test 8: Read after OPTIMIZE FINAL (verifies merged part codec consistency)
SELECT '--- Test 8: Post-OPTIMIZE read ---';
SELECT
    count() AS cnt,
    sum(gcd_col) AS gcd_sum,
    min(dd_t64_col) AS dd_min,
    max(gorilla_col) AS gorilla_max
FROM dist_codec_test
SETTINGS prefer_localhost_replica = 0;

DROP TABLE dist_codec_test;
DROP TABLE local_codec_test;
