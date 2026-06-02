DROP TABLE IF EXISTS dist_04303;
DROP TABLE IF EXISTS dist_04303_local;

CREATE TABLE dist_04303_local
(
    d Date,
    id UInt32,
    version UInt32,
    value String
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(d)
ORDER BY (d, id)
SETTINGS min_bytes_for_wide_part = 0, index_granularity = 1;

CREATE TABLE dist_04303 AS dist_04303_local
ENGINE = Distributed(test_shard_localhost, currentDatabase(), dist_04303_local, id);

SET insert_distributed_sync = 1;
SET optimize_move_to_prewhere = 1;

INSERT INTO dist_04303_local VALUES
('2024-01-01', 1, 1, 'old_jan'),
('2024-01-01', 1, 2, 'new_jan'),
('2024-01-02', 2, 1, 'keep_jan'),
('2024-02-01', 1, 1, 'old_feb');

INSERT INTO dist_04303_local VALUES
('2024-02-01', 1, 2, 'new_feb'),
('2024-02-02', 3, 1, 'keep_feb');

SELECT d, id, value
FROM dist_04303
FINAL
PREWHERE id IN (1, 2)
WHERE d < '2024-02-01'
ORDER BY d, id;

SELECT count(), min(value), max(value)
FROM dist_04303
FINAL
PREWHERE id = 1
WHERE d >= '2024-02-01';

DROP TABLE dist_04303;
DROP TABLE dist_04303_local;
