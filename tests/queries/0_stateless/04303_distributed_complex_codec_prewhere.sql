-- Tags: distributed

DROP TABLE IF EXISTS local_codec_test;
DROP TABLE IF EXISTS dist_codec_test;

-- 创建包含混合高级 Codec 的本地列式表
CREATE TABLE local_codec_test
(
    id UInt64 CODEC(Delta, ZSTD(1)),
    metric_a Float64 CODEC(Gorilla, LZ4),
    metric_b Int32 CODEC(T64, ZSTD(2)),
    category String CODEC(ZSTD(3))
)
ENGINE = MergeTree
ORDER BY id
SETTINGS index_granularity = 256;

-- 创建基于测试集群（自带的两分片集群）的分布式表
CREATE TABLE dist_codec_test AS local_codec_test
ENGINE = Distributed(test_cluster_two_shards, currentDatabase(), local_codec_test, id);

-- 插入用于触发压缩字典特性的周期性数据
INSERT INTO local_codec_test 
SELECT 
    number, 
    number * 0.1, 
    number % 1000, 
    'cat_' || toString(number % 5)
FROM numbers(10000);

-- 强制触发分布式键优化及网络通信
SET optimize_distributed_group_by_sharding_key = 1;
SET optimize_skip_unused_shards = 1;
SET prefer_localhost_replica = 0;

-- Test 1: 盲区验证 - Delta Codec 被用于 PREWHERE 寻址，Gorilla 被用于 SELECT 聚合
SELECT count(), round(sum(metric_a), 2)
FROM dist_codec_test
PREWHERE id > 2000 AND id <= 8000;

-- Test 2: 盲区验证 - String ZSTD 被用于 PREWHERE 寻址，T64 穿透分布式边界
SELECT category, max(metric_b)
FROM dist_codec_test
PREWHERE category = 'cat_3'
GROUP BY category
ORDER BY category;

-- Test 3: 盲区验证 - 多 Codec 复杂谓词组合穿透 Distributed
SELECT count()
FROM dist_codec_test
PREWHERE id % 2 = 0 AND metric_b > 500 AND metric_a > 100.5;

DROP TABLE dist_codec_test;
DROP TABLE local_codec_test;
