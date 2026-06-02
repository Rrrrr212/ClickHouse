DROP TABLE IF EXISTS remote_codec_wide;
DROP TABLE IF EXISTS remote_codec_compact;
DROP TABLE IF EXISTS remote_codec_dest;

CREATE TABLE remote_codec_wide
(
    id UInt64 CODEC(Delta(4), ZSTD(5)),
    ts DateTime CODEC(DoubleDelta, ZSTD(3)),
    msg String CODEC(ZSTD(12)),
    score Float32 CODEC(Gorilla, LZ4)
) ENGINE = MergeTree ORDER BY id
SETTINGS min_bytes_for_wide_part = 0, min_bytes_for_full_part_storage = 0;

CREATE TABLE remote_codec_compact
(
    id UInt64 CODEC(Delta(4), ZSTD(5)),
    ts DateTime CODEC(DoubleDelta, ZSTD(3)),
    msg String CODEC(ZSTD(12)),
    score Float32 CODEC(Gorilla, LZ4)
) ENGINE = MergeTree ORDER BY id
SETTINGS min_rows_for_wide_part = 100000, min_bytes_for_wide_part = 10000000;

INSERT INTO remote_codec_wide SELECT
    number,
    toDateTime('2020-01-01 00:00:00') + number * 60,
    concat('message_text_', toString(number % 1000)),
    sin(number * 0.05)
FROM numbers(3000);

INSERT INTO remote_codec_compact SELECT
    number + 3000,
    toDateTime('2020-01-01 00:00:00') + (number + 3000) * 60,
    concat('message_text_', toString((number + 3000) % 1000)),
    sin((number + 3000) * 0.05)
FROM numbers(500);

SELECT '--- remote wide ---';
SELECT count(), sum(id), floor(avg(score), 6), min(msg), max(msg)
FROM remote('127.0.0.1', currentDatabase(), remote_codec_wide);

SELECT '--- remote compact ---';
SELECT count(), sum(id), floor(avg(score), 6), min(msg), max(msg)
FROM remote('127.0.0.1', currentDatabase(), remote_codec_compact);

SELECT '--- remote union wide and compact ---';
SELECT count(), sum(id), floor(avg(score), 6)
FROM remote('127.0.0.1', currentDatabase(), remote_codec_wide)
UNION ALL
SELECT count(), sum(id), floor(avg(score), 6)
FROM remote('127.0.0.1', currentDatabase(), remote_codec_compact);

SELECT '--- local join over remote codec tables ---';
SELECT count(), sum(w.id) + sum(c.id)
FROM remote_codec_wide AS w
INNER JOIN remote('127.0.0.1', currentDatabase(), remote_codec_compact) AS c
ON w.id % 1000 = c.id % 1000;

CREATE TABLE remote_codec_dest
(
    id UInt64 CODEC(T64, ZSTD(3)),
    ts DateTime CODEC(DoubleDelta, ZSTD(3)),
    msg String CODEC(ZSTD(12)),
    score Float32 CODEC(Gorilla, LZ4)
) ENGINE = MergeTree ORDER BY id
SETTINGS min_bytes_for_wide_part = 0;

INSERT INTO remote_codec_dest SELECT * FROM remote('127.0.0.1', currentDatabase(), remote_codec_wide);

SELECT count(), sum(id), floor(avg(score), 6) FROM remote_codec_dest;

DROP TABLE IF EXISTS remote_codec_wide;
DROP TABLE IF EXISTS remote_codec_compact;
DROP TABLE IF EXISTS remote_codec_dest;