-- Tags: no-parallel, long
--
-- Test for distributed query sharding key aggregation optimizations
-- Covers cases that may be affected by changes in MergeTreeData.cpp, aggregator, or distributed query handling
--

-- Test 1: Distributed table setup with various sharding keys
DROP TABLE IF EXISTS local_shard_test_1;
DROP TABLE IF EXISTS local_shard_test_2;
DROP TABLE IF EXISTS distributed_shard_test;

-- Create first shard table
CREATE TABLE local_shard_test_1
(
    shard_key UInt64,
    value1 UInt64,
    value2 Float64,
    data String,
    ts DateTime
)
ENGINE = MergeTree()
ORDER BY (shard_key, ts)
SETTINGS index_granularity = 1024;

-- Create second shard table
CREATE TABLE local_shard_test_2 AS local_shard_test_1
ENGINE = MergeTree()
ORDER BY (shard_key, ts);

-- Create distributed table (simulating cluster)
CREATE TABLE distributed_shard_test AS local_shard_test_1
ENGINE = MergeTree()
ORDER BY (shard_key, ts);

-- Test 2: Insert data distributed by shard key
-- Even shard keys go to "shard 1", odd to "shard 2"
INSERT INTO local_shard_test_1
SELECT
    number * 2 AS shard_key,
    number,
    number * 1.5,
    toString(number),
    now()
FROM numbers(5000);

INSERT INTO local_shard_test_2
SELECT
    number * 2 + 1 AS shard_key,
    number * 10,
    number * 3.5,
    toString(number * 10),
    now()
FROM numbers(5000);

-- Test 3: Aggregation grouped by shard key (should be optimizable)
SELECT
    'group_by_shard_key',
    shard_key % 10,
    count(),
    sum(value1),
    avg(value2),
    max(length(data))
FROM (
    SELECT * FROM local_shard_test_1
    UNION ALL
    SELECT * FROM local_shard_test_2
)
GROUP BY shard_key % 10
ORDER BY shard_key % 10;

-- Test 4: Aggregation with prewhere on shard key
SELECT
    'prewhere_on_shard_key',
    count(),
    sum(value1),
    avg(value2)
FROM (
    SELECT * FROM local_shard_test_1
    UNION ALL
    SELECT * FROM local_shard_test_2
)
PREWHERE shard_key BETWEEN 2000 AND 4000
WHERE value2 > 500;

-- Test 5: Window functions with partition by shard key
SELECT
    'window_by_shard_key',
    shard_key % 5,
    count(),
    max(rolling_sum)
FROM (
    SELECT
        shard_key,
        sum(value1) OVER (PARTITION BY shard_key % 5 ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS rolling_sum
    FROM (
        SELECT * FROM local_shard_test_1
        UNION ALL
        SELECT * FROM local_shard_test_2
    )
)
GROUP BY shard_key % 5
ORDER BY shard_key % 5;

-- Test 6: Join on shard key
SELECT
    'join_on_shard_key',
    count(),
    sum(a.value1 + b.value1),
    avg(a.value2 + b.value2)
FROM (
    SELECT * FROM local_shard_test_1 WHERE shard_key % 4 = 0
) a
INNER JOIN (
    SELECT * FROM local_shard_test_2 WHERE shard_key % 4 = 1
) b ON a.shard_key + 1 = b.shard_key;

-- Test 7: Aggregation with quantiles and sharding key
SELECT
    'quantiles_on_shards',
    shard_key % 8,
    quantile(0.25)(value2),
    quantile(0.5)(value2),
    quantile(0.75)(value2),
    quantileExact(0.9)(value1)
FROM (
    SELECT * FROM local_shard_test_1
    UNION ALL
    SELECT * FROM local_shard_test_2
)
GROUP BY shard_key % 8
ORDER BY shard_key % 8;

-- Test 8: Optimize FINAL with sharding key
OPTIMIZE TABLE local_shard_test_1 FINAL;
OPTIMIZE TABLE local_shard_test_2 FINAL;

SELECT
    'after_final',
    count(),
    sum(value1)
FROM (
    SELECT * FROM local_shard_test_1
    UNION ALL
    SELECT * FROM local_shard_test_2
);

-- Test 9: Aggregation with limit by sharding key
SELECT
    'limit_by_shard_key',
    shard_key % 3,
    count(),
    sum(value1)
FROM (
    SELECT * FROM local_shard_test_1
    UNION ALL
    SELECT * FROM local_shard_test_2
)
LIMIT 10 BY shard_key % 3
ORDER BY shard_key % 3, value1 DESC;

-- Cleanup
DROP TABLE local_shard_test_1;
DROP TABLE local_shard_test_2;
DROP TABLE distributed_shard_test;
