-- Tags: no-fasttest
--
-- Regression test for distributed query + compression codec + parallel replicas.
-- Covers the gap where parallel replicas read compressed data from MergeTree
-- parts with non-default codecs, and the coordinator merges decompressed blocks.
--
-- Bug scenario: when parallel replicas are enabled, each replica reads a
-- subset of granules from the same part. If the codec decompression buffer
-- is shared or not properly reset between granules, data corruption can
-- occur silently. This test verifies that each replica correctly decompresses
-- its assigned granules and the coordinator merges them correctly.

DROP TABLE IF EXISTS pr_codec_test;

CREATE TABLE pr_codec_test
(
    id UInt64,
    shard_id UInt8,
    -- Multiple codec columns to exercise different decompression paths
    gcd_col UInt64 CODEC(GCD, LZ4),
    dd_col Int64 CODEC(DoubleDelta, T64, ZSTD),
    gorilla_col Float64 CODEC(Gorilla),
    str_col String CODEC(ZSTD(1)),
    payload String  -- no codec, baseline
)
ENGINE = MergeTree
PARTITION BY shard_id
ORDER BY id
SETTINGS
    index_granularity = 8192,
    min_bytes_for_wide_part = 0,
    min_rows_for_wide_part = 0;

-- Insert data across multiple partitions to ensure granule distribution
INSERT INTO pr_codec_test
SELECT
    number AS id,
    number % 4 AS shard_id,
    number * 13 AS gcd_col,
    toInt64(number * 1000) AS dd_col,
    number * 0.125 AS gorilla_col,
    toString(number % 500) AS str_col,
    repeat('x', 100) AS payload
FROM numbers(200000);

OPTIMIZE TABLE pr_codec_test FINAL;

-- Test 1: Parallel replicas with partial codec column read
SELECT '--- Test 1: PR partial codec read ---';
SELECT
    count() AS cnt,
    sum(gcd_col) AS gcd_sum,
    sum(dd_col) AS dd_sum
FROM pr_codec_test
SETTINGS
    enable_parallel_replicas = 1,
    max_parallel_replicas = 4,
    parallel_replicas_for_non_replicated_merge_tree = 1,
    cluster_for_parallel_replicas = 'parallel_replicas';

-- Test 2: Parallel replicas with all codec columns
SELECT '--- Test 2: PR all codec columns ---';
SELECT
    count() AS cnt,
    sum(gcd_col) AS gcd_sum,
    min(dd_col) AS dd_min,
    max(gorilla_col) AS gorilla_max,
    countDistinct(str_col) AS str_distinct
FROM pr_codec_test
SETTINGS
    enable_parallel_replicas = 1,
    max_parallel_replicas = 4,
    parallel_replicas_for_non_replicated_merge_tree = 1,
    cluster_for_parallel_replicas = 'parallel_replicas';

-- Test 3: Parallel replicas + GROUP BY on codec column
SELECT '--- Test 3: PR GROUP BY codec column ---';
SELECT
    gcd_col % 13 = 0 AS divisible,
    count() AS cnt,
    sum(dd_col) AS dd_sum
FROM pr_codec_test
GROUP BY divisible
ORDER BY divisible
SETTINGS
    enable_parallel_replicas = 1,
    max_parallel_replicas = 4,
    parallel_replicas_for_non_replicated_merge_tree = 1,
    cluster_for_parallel_replicas = 'parallel_replicas';

-- Test 4: Parallel replicas + ORDER BY on codec column
SELECT '--- Test 4: PR ORDER BY codec column ---';
SELECT id, gcd_col, dd_col
FROM pr_codec_test
ORDER BY id
LIMIT 20
SETTINGS
    enable_parallel_replicas = 1,
    max_parallel_replicas = 4,
    parallel_replicas_for_non_replicated_merge_tree = 1,
    cluster_for_parallel_replicas = 'parallel_replicas';

-- Test 5: Parallel replicas + WHERE on compressed column
SELECT '--- Test 5: PR WHERE on compressed column ---';
SELECT count(), sum(gcd_col)
FROM pr_codec_test
WHERE gorilla_col > 10000.0
SETTINGS
    enable_parallel_replicas = 1,
    max_parallel_replicas = 4,
    parallel_replicas_for_non_replicated_merge_tree = 1,
    cluster_for_parallel_replicas = 'parallel_replicas';

-- Test 6: Verify correctness against non-PR execution
SELECT '--- Test 6: PR vs non-PR correctness ---';
SELECT
    (SELECT sum(gcd_col) FROM pr_codec_test
     SETTINGS enable_parallel_replicas = 1, max_parallel_replicas = 4,
              parallel_replicas_for_non_replicated_merge_tree = 1,
              cluster_for_parallel_replicas = 'parallel_replicas')
    =
    (SELECT sum(gcd_col) FROM pr_codec_test
     SETTINGS enable_parallel_replicas = 0) AS gcd_match,
    (SELECT sum(dd_col) FROM pr_codec_test
     SETTINGS enable_parallel_replicas = 1, max_parallel_replicas = 4,
              parallel_replicas_for_non_replicated_merge_tree = 1,
              cluster_for_parallel_replicas = 'parallel_replicas')
    =
    (SELECT sum(dd_col) FROM pr_codec_test
     SETTINGS enable_parallel_replicas = 0) AS dd_match,
    (SELECT sum(gorilla_col) FROM pr_codec_test
     SETTINGS enable_parallel_replicas = 1, max_parallel_replicas = 4,
              parallel_replicas_for_non_replicated_merge_tree = 1,
              cluster_for_parallel_replicas = 'parallel_replicas')
    =
    (SELECT sum(gorilla_col) FROM pr_codec_test
     SETTINGS enable_parallel_replicas = 0) AS gorilla_match;

DROP TABLE pr_codec_test;
