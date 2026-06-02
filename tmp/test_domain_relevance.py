#!/usr/bin/env python3
import sys
sys.path.insert(0, "/app/ClickHouse")
from ci.jobs.scripts.find_tests import Targeting

print("=== Test _extract_path_domain_keywords ===")

kws = Targeting._extract_path_domain_keywords("src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp")
print(f"Keeper/ZooKeeper path: {kws}")
kw_lower = {k.lower() for k in kws}
assert "keeper" in kw_lower, f"FAIL: keeper not found in {kws}"
assert "zoo" in kw_lower, f"FAIL: zoo not found in {kws}"
print("  PASS")

kws = Targeting._extract_path_domain_keywords("src/Processors/Formats/Impl/Parquet/ParquetDecoding.cpp")
print(f"Parquet path: {kws}")
kw_lower = {k.lower() for k in kws}
assert "parquet" in kw_lower, f"FAIL: parquet not found in {kws}"
print("  PASS")

kws = Targeting._extract_path_domain_keywords("src/Common/ThreadPool.cpp")
print(f"Generic path: {kws}")
assert len(kws) == 0, f"FAIL: expected empty for generic path, got {kws}"
print("  PASS")

kws = Targeting._extract_path_domain_keywords("src/Storages/MergeTree/MergeTreeData.cpp")
print(f"MergeTree path: {kws}")
assert len(kws) == 0, f"FAIL: expected empty for MergeTree path, got {kws}"
print("  PASS")

print()
print("=== Test _compute_domain_relevance ===")

domain_kws = ["Zoo", "Keeper", "KeeperClientCLI", "Commands"]

dr = Targeting._compute_domain_relevance("04068_keeper_client_watch_deleted_event", domain_kws)
print(f"keeper test: {dr}")
assert dr > 1.0, f"FAIL: expected boost, got {dr}"
print("  PASS")

dr = Targeting._compute_domain_relevance("01505_pipeline_executor_UAF", domain_kws)
print(f"UAF test: {dr}")
assert dr == 0.35, f"FAIL: expected 0.35, got {dr}"
print("  PASS")

dr = Targeting._compute_domain_relevance("03988_zookeeper_send_receive_race", domain_kws)
print(f"zookeeper test: {dr}")
assert dr > 1.0, f"FAIL: expected boost, got {dr}"
print("  PASS")

dr = Targeting._compute_domain_relevance("01505_pipeline_executor_UAF", [])
print(f"no keywords: {dr}")
assert dr == 1.0, f"FAIL: expected 1.0, got {dr}"
print("  PASS")

print()
print("All tests passed!")