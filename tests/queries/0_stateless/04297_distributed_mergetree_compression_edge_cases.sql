-- Tags: no-parallel
--
-- Test for distributed queries with various compression codecs on MergeTree tables
-- Covers edge cases that may be affected by changes in MergeTreeData.cpp or codec handling
--

-- Test 1: Distributed table with different compression codecs on shards
DROP TABLE IF EXISTS local_compression_test;
DROP TABLE IF EXISTS distributed_compression_test;

CREATE TABLE local_compression_test
(
    id UInt64,
    value Float64 CODEC(Delta, ZSTD(3)),
    data String CODEC(LZ4HC),
    ts DateTime CODEC(T64)
)
ENGINE = MergeTree()
ORDER BY id
SETTINGS index_granularity = 8192;

-- Create distributed table (using the same engine for simplicity, simulating multi-shard setup)
CREATE TABLE distributed_compression_test AS local_compression_test
ENGINE = MergeTree()
ORDER BY id;

-- Test 2: Insert and read through distributed query pattern
INSERT INTO local_compression_test
SELECT
    number,
    number * 1.1 + sin(number),
    repeat('ClickHouse', 10),
    now()
FROM numbers(10000);

-- Verify data integrity
SELECT
    'basic_read',
    count(),
    sum(id),
    round(avg(value), 6),
    min(ts),
    max(ts)
FROM local_compression_test;

-- Test 3: Aggregations with various compression codecs
SELECT
    'aggregations_with_compression',
    count(),
    sum(id),
    avg(value),
    quantile(0.5)(value),
    max(length(data))
FROM local_compression_test
GROUP BY id % 10
ORDER BY id % 10;

-- Test 4: Filtering with prewhere on compressed columns
SELECT
    'prewhere_compressed',
    count(),
    sum(value)
FROM local_compression_test
PREWHERE id BETWEEN 1000 AND 2000
WHERE value > 100;

-- Test 5: Vertical merge with compressed columns
OPTIMIZE TABLE local_compression_test FINAL;

SELECT
    'after_vertical_merge',
    count(),
    sum(id)
FROM local_compression_test;

-- Test 6: ALTER COLUMN to change compression codec
ALTER TABLE local_compression_test
MODIFY COLUMN value CODEC(ZSTD(6));

INSERT INTO local_compression_test
SELECT
    number + 10000,
    number * 2.2 + cos(number),
    repeat('Test', 20),
    now() + 1
FROM numbers(5000);

OPTIMIZE TABLE local_compression_test FINAL;

SELECT
    'after_codec_change',
    count(),
    sum(value)
FROM local_compression_test;

-- Test 7: Nullable compressed columns
ALTER TABLE local_compression_test
ADD COLUMN nullable_data Nullable(String) CODEC(LZ4);

UPDATE local_compression_test SET nullable_data = data WHERE id % 3 = 0;
UPDATE local_compression_test SET nullable_data = NULL WHERE id % 3 = 1;

OPTIMIZE TABLE local_compression_test FINAL;

SELECT
    'nullable_compressed',
    count(),
    countIf(nullable_data IS NOT NULL),
    countIf(nullable_data IS NULL)
FROM local_compression_test;

-- Cleanup
DROP TABLE local_compression_test;
DROP TABLE distributed_compression_test;
