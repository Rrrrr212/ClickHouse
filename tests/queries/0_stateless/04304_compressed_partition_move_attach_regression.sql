DROP TABLE IF EXISTS src_04304;
DROP TABLE IF EXISTS dst_04304;

CREATE TABLE src_04304
(
    p UInt8,
    id UInt32,
    payload String CODEC(ZSTD(1))
)
ENGINE = MergeTree
PARTITION BY p
ORDER BY id
SETTINGS compress_marks = 1, min_bytes_for_wide_part = 0, index_granularity = 1;

CREATE TABLE dst_04304 AS src_04304
ENGINE = MergeTree
PARTITION BY p
ORDER BY id
SETTINGS compress_marks = 1, min_bytes_for_wide_part = 0, index_granularity = 1;

INSERT INTO src_04304 VALUES
(1, 10, 'alpha'),
(1, 20, 'beta'),
(2, 30, 'gamma'),
(2, 40, 'delta');

OPTIMIZE TABLE src_04304 FINAL;

ALTER TABLE src_04304 MOVE PARTITION 1 TO TABLE dst_04304;

SELECT 'after_move';
SELECT p, id, payload FROM src_04304 ORDER BY p, id;
SELECT p, id, payload FROM dst_04304 ORDER BY p, id;

ALTER TABLE dst_04304 DETACH PARTITION 1;
ALTER TABLE dst_04304 ATTACH PARTITION 1;

SELECT 'after_attach';
SELECT count(), min(payload), max(payload) FROM dst_04304 WHERE p = 1;
SELECT p, id, payload FROM dst_04304 ORDER BY p, id;

DROP TABLE src_04304;
DROP TABLE dst_04304;
