DROP TABLE IF EXISTS global_in_src_wide;
DROP TABLE IF EXISTS global_in_sink;

CREATE TABLE global_in_src_wide
(
    id UInt64 CODEC(Delta, ZSTD(3)),
    name String CODEC(ZSTD(9)),
    val Float64 CODEC(Gorilla, LZ4)
) ENGINE = MergeTree ORDER BY id
SETTINGS min_bytes_for_wide_part = 0, min_bytes_for_full_part_storage = 0;

CREATE TABLE global_in_sink
(
    id UInt64 CODEC(Delta, ZSTD(3)),
    name String CODEC(ZSTD(9)),
    val Float64 CODEC(Gorilla, LZ4)
) ENGINE = MergeTree ORDER BY id
SETTINGS min_bytes_for_wide_part = 0, min_bytes_for_full_part_storage = 0;

INSERT INTO global_in_src_wide SELECT
    number,
    concat('row_', toString(number % 500)),
    sin(number * 0.1)
FROM numbers(5000);

INSERT INTO global_in_sink SELECT
    number + 2500,
    concat('row_', toString(number % 500)),
    cos(number * 0.1)
FROM numbers(5000);

SYSTEM STOP MERGES global_in_src_wide;
SYSTEM STOP MERGES global_in_sink;

SELECT count() FROM global_in_src_wide WHERE id IN
(
    SELECT id FROM global_in_sink WHERE name GLOBAL IN
    (
        SELECT name FROM global_in_src_wide WHERE val > 0.5
    )
);

SELECT count() FROM global_in_sink WHERE id GLOBAL IN
(
    SELECT id FROM global_in_src_wide WHERE name GLOBAL IN
    (
        SELECT name FROM global_in_sink WHERE val < 0
    )
);

SELECT sum(id), countDistinct(name) FROM global_in_src_wide WHERE name IN
(
    SELECT DISTINCT name FROM global_in_sink WHERE id GLOBAL IN
    (
        SELECT id FROM global_in_src_wide WHERE val BETWEEN 0.0 AND 1.0
    )
);

DROP TABLE IF EXISTS global_in_src_wide;
DROP TABLE IF EXISTS global_in_sink;