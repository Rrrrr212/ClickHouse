DROP TABLE IF EXISTS dist_merge_codec_shard1;
DROP TABLE IF EXISTS dist_merge_codec_shard2;
DROP TABLE IF EXISTS dist_merge_codec_dist;
DROP TABLE IF EXISTS dist_merge_codec_merge;

CREATE TABLE dist_merge_codec_shard1
(
    id UInt64 CODEC(Delta, ZSTD(3)),
    name String CODEC(ZSTD(7)),
    val Float64 CODEC(Gorilla, LZ4)
) ENGINE = MergeTree ORDER BY id
SETTINGS min_bytes_for_wide_part = 0;

CREATE TABLE dist_merge_codec_shard2
(
    id UInt64 CODEC(Delta, ZSTD(3)),
    name String CODEC(ZSTD(7)),
    val Float64 CODEC(Gorilla, LZ4)
) ENGINE = MergeTree ORDER BY id
SETTINGS min_bytes_for_wide_part = 0;

CREATE TABLE dist_merge_codec_dist
(
    id UInt64,
    name String,
    val Float64
) ENGINE = Distributed('test_cluster_two_shards_localhost', currentDatabase(), dist_merge_codec_shard1, id);

CREATE TABLE dist_merge_codec_merge
(
    id UInt64,
    name String,
    val Float64
) ENGINE = Merge(currentDatabase(), '^dist_merge_codec_shard');

INSERT INTO dist_merge_codec_shard1 SELECT number, concat('s1_', toString(number)), sin(number) FROM numbers(3000);
INSERT INTO dist_merge_codec_shard2 SELECT number + 3000, concat('s2_', toString(number + 3000)), cos(number * 0.1) FROM numbers(3000);

SELECT '--- distributed insert into codec tables ---';
INSERT INTO dist_merge_codec_dist SELECT number + 6000, concat('dist_', toString(number + 6000)), number * 0.001 FROM numbers(1000);

SELECT count() FROM dist_merge_codec_shard1;
SELECT count() FROM dist_merge_codec_shard2;

SELECT '--- merge engine across codec tables ---';
SELECT count(), sum(id), floor(min(val), 6), floor(max(val), 6)
FROM dist_merge_codec_merge;

SELECT '--- distributed aggregation with codec tables ---';
SELECT name, floor(sum(val), 6), count()
FROM dist_merge_codec_dist
GROUP BY name
ORDER BY name
LIMIT 5;

SELECT '--- merge engine aggregation with decompression ---';
SELECT floor(sum(val), 6), floor(avg(val), 6)
FROM dist_merge_codec_merge;

DROP TABLE IF EXISTS dist_merge_codec_dist;
DROP TABLE IF EXISTS dist_merge_codec_merge;
DROP TABLE IF EXISTS dist_merge_codec_shard1;
DROP TABLE IF EXISTS dist_merge_codec_shard2;