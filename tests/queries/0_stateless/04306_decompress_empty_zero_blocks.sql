DROP TABLE IF EXISTS empty_decompress_src;

CREATE TABLE empty_decompress_src
(
    id UInt64 CODEC(Delta(8), ZSTD),
    val String CODEC(ZSTD(12))
) ENGINE = MergeTree ORDER BY id
SETTINGS min_bytes_for_wide_part = 0;

INSERT INTO empty_decompress_src SELECT number, concat('data_', toString(number % 100)) FROM numbers(10000);

ALTER TABLE empty_decompress_src DELETE WHERE id % 3 = 0 SETTINGS mutations_sync = 2;

SELECT count(), sum(id) FROM empty_decompress_src;

OPTIMIZE TABLE empty_decompress_src FINAL;

SELECT count(), sum(id) FROM empty_decompress_src;

INSERT INTO empty_decompress_src SELECT number + 10000, '' FROM numbers(500);

SELECT count(), sum(id), length(val) FROM empty_decompress_src WHERE val = '' GROUP BY length(val);

DROP TABLE IF EXISTS empty_decompress_src;

DROP TABLE IF EXISTS empty_range_decompress;

CREATE TABLE empty_range_decompress
(
    id UInt64 CODEC(Delta, ZSTD),
    category LowCardinality(String),
    val Float64 CODEC(Gorilla, ZSTD)
) ENGINE = MergeTree ORDER BY (category, id)
SETTINGS min_bytes_for_wide_part = 0;

INSERT INTO empty_range_decompress SELECT
    number,
    toString(number % 10),
    number * 0.001
FROM numbers(10000);

ALTER TABLE empty_range_decompress DELETE WHERE category = '5' SETTINGS mutations_sync = 2;

SELECT count(), sum(id), floor(sum(val), 6) FROM empty_range_decompress;

OPTIMIZE TABLE empty_range_decompress FINAL;

SELECT count(), sum(id), floor(sum(val), 6) FROM empty_range_decompress;

SELECT count(), min(category), max(category) FROM empty_range_decompress;

DROP TABLE IF EXISTS empty_range_decompress;