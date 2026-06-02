DROP TABLE IF EXISTS repl_codec_alter SYNC;

CREATE TABLE repl_codec_alter
(
    id UInt64,
    val UInt64 CODEC(Delta, ZSTD(3)),
    name String CODEC(ZSTD(5))
) ENGINE = ReplicatedMergeTree('/clickhouse/{database}/tables/repl_codec_alter', 'r1')
ORDER BY id
SETTINGS min_bytes_for_wide_part = 0;

INSERT INTO repl_codec_alter SELECT number, number * 100, concat('text_', toString(number)) FROM numbers(1000);
INSERT INTO repl_codec_alter SELECT number + 1000, (number + 1000) * 100, concat('text_', toString(number + 1000)) FROM numbers(1000);

SYSTEM SYNC REPLICA repl_codec_alter;

SELECT count(), sum(val), min(name), max(name) FROM repl_codec_alter;

ALTER TABLE repl_codec_alter MODIFY COLUMN val CODEC(ZSTD(9), Delta, LZ4HC) SETTINGS replication_alter_partitions_sync = 2;

SELECT count(), sum(val), min(name), max(name) FROM repl_codec_alter;

INSERT INTO repl_codec_alter SELECT number + 2000, (number + 2000) * 100, concat('new_text_', toString(number + 2000)) FROM numbers(500);

SELECT count(), sum(val), min(name), max(name) FROM repl_codec_alter;

OPTIMIZE TABLE repl_codec_alter FINAL;

SYSTEM SYNC REPLICA repl_codec_alter;

SELECT count(), sum(val), min(name), max(name) FROM repl_codec_alter;

SELECT default_compression_codec
FROM system.parts
WHERE database = currentDatabase() AND table = 'repl_codec_alter' AND active
ORDER BY name;

DROP TABLE IF EXISTS repl_codec_alter SYNC;