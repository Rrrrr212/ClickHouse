"""
Unit tests for semantic_path_filter module.

Covers:
  - CamelCase splitting
  - Path keyword extraction
  - Domain identification for source files
  - Test relevance scoring
  - End-to-end filtering for the Keeper scenario
  - Cross-domain isolation (pipeline tests excluded for Keeper changes)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from semantic_path_filter import (
    Domain,
    DomainDef,
    DOMAIN_DEFINITIONS,
    _normalise_path,
    _path_keywords,
    _split_camel_case,
    _matches_any_pattern,
    identify_source_domains,
    score_test_relevance,
    filter_tests,
    explain_relevance,
    is_test_semantically_relevant,
    SourceDomainInfo,
    TestRelevanceScore,
    RELEVANCE_THRESHOLD,
)


class TestSplitCamelCase(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(_split_camel_case("KeeperClient"), ["keeper", "client"])

    def test_three_words(self):
        self.assertEqual(
            _split_camel_case("KeeperClientCLI"), ["keeper", "client", "cli"]
        )

    def test_single_word(self):
        self.assertEqual(_split_camel_case("Commands"), ["commands"])

    def test_all_upper(self):
        self.assertEqual(_split_camel_case("UAF"), [])

    def test_mixed(self):
        result = _split_camel_case("MergeTreeData")
        self.assertIn("merge", result)
        self.assertIn("tree", result)
        self.assertIn("data", result)

    def test_lowercase(self):
        self.assertEqual(_split_camel_case("commands"), ["commands"])


class TestPathKeywords(unittest.TestCase):
    def test_keeper_client_cli_path(self):
        kw = _path_keywords("src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp")
        self.assertIn("keeper", kw)
        self.assertIn("client", kw)
        self.assertIn("cli", kw)
        self.assertIn("zookeeper", kw)
        self.assertIn("commands", kw)
        self.assertIn("common", kw)

    def test_pipeline_test_path(self):
        kw = _path_keywords("tests/queries/0_stateless/01505_pipeline_executor_UAF.sh")
        self.assertIn("pipeline", kw)
        self.assertIn("executor", kw)

    def test_keeper_test_path(self):
        kw = _path_keywords(
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh"
        )
        self.assertIn("keeper", kw)
        self.assertIn("client", kw)
        self.assertIn("lsr", kw)
        self.assertIn("commands", kw)

    def test_integration_test_path(self):
        kw = _path_keywords("tests/integration/test_keeper_client/test.py")
        self.assertIn("keeper", kw)
        self.assertIn("client", kw)


class TestPatternMatching(unittest.TestCase):
    def test_keeper_source_pattern(self):
        self.assertTrue(
            _matches_any_pattern(
                "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp",
                frozenset({"src/Common/ZooKeeper/KeeperClientCLI/*"}),
            )
        )

    def test_keeper_test_pattern(self):
        self.assertTrue(
            _matches_any_pattern(
                "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
                frozenset({"tests/queries/*/0*keeper*"}),
            )
        )

    def test_pipeline_test_no_match_keeper_pattern(self):
        self.assertFalse(
            _matches_any_pattern(
                "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
                frozenset({"tests/queries/*/0*keeper*"}),
            )
        )


class TestIdentifySourceDomains(unittest.TestCase):
    def test_keeper_client_cli(self):
        info = identify_source_domains(
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"
        )
        self.assertIn(Domain.KEEPER, info.domains)
        self.assertIn(Domain.ZOOKEEPER, info.domains)
        self.assertNotIn(Domain.PIPELINE, info.domains)
        self.assertGreater(len(info.matched_definitions), 0)

    def test_pipeline_source(self):
        info = identify_source_domains("src/Processors/Pipeline.cpp")
        self.assertIn(Domain.PIPELINE, info.domains)
        self.assertNotIn(Domain.KEEPER, info.domains)

    def test_merge_tree_source(self):
        info = identify_source_domains("src/Storages/MergeTree/MergeTreeData.cpp")
        self.assertIn(Domain.MERGE_TREE, info.domains)

    def test_unknown_source(self):
        info = identify_source_domains("src/SomeRandomFile.cpp")
        self.assertIn(Domain.UNKNOWN, info.domains)


class TestScoreTestRelevance(unittest.TestCase):
    def test_keeper_test_for_keeper_source(self):
        source_info = identify_source_domains(
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"
        )
        relevance = score_test_relevance(
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
            source_info,
        )
        self.assertGreater(relevance.score, 0)
        self.assertTrue(relevance.is_relevant)
        self.assertIn(Domain.KEEPER, relevance.matched_domains)

    def test_pipeline_test_for_keeper_source(self):
        source_info = identify_source_domains(
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"
        )
        relevance = score_test_relevance(
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
            source_info,
        )
        self.assertEqual(relevance.score, 0.0)
        self.assertFalse(relevance.is_relevant)

    def test_zookeeper_test_for_keeper_source(self):
        source_info = identify_source_domains(
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"
        )
        relevance = score_test_relevance(
            "tests/queries/0_stateless/04035_system_zookeeper_watches.sql",
            source_info,
        )
        self.assertGreater(relevance.score, 0)
        self.assertTrue(relevance.is_relevant)

    def test_integration_keeper_test_for_keeper_source(self):
        source_info = identify_source_domains(
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"
        )
        relevance = score_test_relevance(
            "tests/integration/test_keeper_client/test.py",
            source_info,
        )
        self.assertGreater(relevance.score, 0)
        self.assertTrue(relevance.is_relevant)


class TestFilterTests(unittest.TestCase):
    def test_keeper_scenario_filters_pipeline(self):
        changed_files = ["src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"]
        candidates = [
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
            "tests/queries/0_stateless/04061_keeper_client_watch_commands.sh",
            "tests/queries/0_stateless/03988_keeper_client_autocomplete.sh",
            "tests/queries/0_stateless/03161_clickhouse_keeper_client_create_sequential.sh",
            "tests/queries/0_stateless/04035_system_zookeeper_watches.sql",
            "tests/integration/test_keeper_client/test.py",
        ]

        results = filter_tests(changed_files, candidates)
        kept_paths = {path for path, _, _ in results}

        self.assertNotIn(
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh", kept_paths
        )
        self.assertIn(
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
            kept_paths,
        )
        self.assertIn(
            "tests/queries/0_stateless/04061_keeper_client_watch_commands.sh",
            kept_paths,
        )
        self.assertIn(
            "tests/queries/0_stateless/04035_system_zookeeper_watches.sql", kept_paths
        )
        self.assertIn("tests/integration/test_keeper_client/test.py", kept_paths)

    def test_pipeline_source_keeps_pipeline_test(self):
        changed_files = ["src/Processors/Pipeline.cpp"]
        candidates = [
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
        ]

        results = filter_tests(changed_files, candidates)
        kept_paths = {path for path, _, _ in results}

        self.assertIn(
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh", kept_paths
        )
        self.assertNotIn(
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
            kept_paths,
        )

    def test_multiple_changed_files(self):
        changed_files = [
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp",
            "src/Processors/Pipeline.cpp",
        ]
        candidates = [
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
        ]

        results = filter_tests(changed_files, candidates)
        kept_paths = {path for path, _, _ in results}

        self.assertIn(
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh", kept_paths
        )
        self.assertIn(
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
            kept_paths,
        )


class TestIsSemanticallyRelevant(unittest.TestCase):
    def test_keeper_source_keeper_test(self):
        self.assertTrue(
            is_test_semantically_relevant(
                "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp",
                "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
            )
        )

    def test_keeper_source_pipeline_test(self):
        self.assertFalse(
            is_test_semantically_relevant(
                "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp",
                "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
            )
        )

    def test_keeper_source_pipeline_test_below_threshold(self):
        self.assertFalse(
            is_test_semantically_relevant(
                "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp",
                "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
                threshold=5.0,
            )
        )


class TestExplainRelevance(unittest.TestCase):
    def test_explain_returns_string(self):
        explanation = explain_relevance(
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp",
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
        )
        self.assertIsInstance(explanation, str)
        self.assertIn("IRRELEVANT", explanation)

    def test_explain_relevant(self):
        explanation = explain_relevance(
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp",
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
        )
        self.assertIn("RELEVANT", explanation)


class TestPrecisionRecallOnKeeperScenario(unittest.TestCase):
    """
    Simulates the exact scenario from the task:
    - PR modifies KeeperClientCLI/Commands.cpp
    - Old algorithm selected 01505_pipeline_executor_UAF (irrelevant)
    - New algorithm should filter it out

    We measure precision and recall against a ground truth where
    Keeper/ZooKeeper tests are the true relevant set.
    """

    def test_precision_recall(self):
        changed_file = "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"

        true_relevant = [
            "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
            "tests/queries/0_stateless/04061_keeper_client_watch_commands.sh",
            "tests/queries/0_stateless/03988_keeper_client_autocomplete.sh",
            "tests/queries/0_stateless/03161_clickhouse_keeper_client_create_sequential.sh",
            "tests/queries/0_stateless/03135_keeper_client_find_commands.sh",
            "tests/queries/0_stateless/02882_clickhouse_keeper_client_no_confirmation.sh",
            "tests/queries/0_stateless/04068_keeper_client_watch_deleted_event.sh",
            "tests/queries/0_stateless/04035_system_zookeeper_watches.sql",
            "tests/queries/0_stateless/02976_system_zookeeper_filters.sql",
            "tests/queries/0_stateless/02417_keeper_map_create_drop.sql",
            "tests/queries/0_stateless/02418_keeper_map_keys_limit.reference",
            "tests/queries/0_stateless/03653_keeper_histogram_metrics.reference",
            "tests/queries/0_stateless/03541_keeper_map_filter_keys.reference",
            "tests/queries/0_stateless/03236_keeper_map_engine_parameters.sql",
            "tests/queries/0_stateless/02911_backup_restore_keeper_map.sh",
            "tests/queries/0_stateless/04077_part_moves_between_shards_keeper_component.reference",
            "tests/queries/0_stateless/02887_insert_quorum_wo_keeper_retries.reference",
            "tests/integration/test_keeper_client/test.py",
            "tests/integration/test_keeper_client_config/test.py",
            "tests/integration/test_keeper_four_word_command/test.py",
            "tests/integration/test_keeper_http_control_cli/test.py",
            "tests/integration/test_keeper_snapshots/test.py",
            "tests/integration/test_keeper_session/test.py",
            "tests/integration/test_keeper_multinode_simple/test.py",
            "tests/integration/test_keeper_secure_client/test.py",
            "tests/integration/test_keeper_auth/test.py",
            "tests/integration/test_keeper_map/test.py",
            "tests/integration/test_keeper_compression/test.py",
            "tests/integration/test_keeper_and_access_storage/test.py",
            "tests/integration/test_alternative_keeper_config/test.py",
            "tests/integration/test_keeper_zookeeper_converter/test.py",
        ]

        irrelevant = [
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
            "tests/queries/0_stateless/00980_zookeeper_merge_tree_alter_settings.sql",
            "tests/queries/0_stateless/01508_race_condition_rename_clear_zookeeper_long.sh",
            "tests/queries/0_stateless/01307_multiple_leaders_zookeeper.sh",
            "tests/queries/0_stateless/00029_test_zookeeper_optimize_exception.sh",
            "tests/queries/0_stateless/02311_system_zookeeper_insert.sql",
            "tests/queries/0_stateless/01158_zookeeper_log_long.sql",
            "tests/queries/0_stateless/00732_quorum_insert_lost_part_zookeeper_long.sql",
            "tests/queries/0_stateless/00661_optimize_final_replicated_without_partition_zookeeper.sql",
            "tests/queries/0_stateless/00510_materizlized_view_and_deduplication_zookeeper.sql",
            "tests/queries/0_stateless/00446_clear_column_in_partition_concurrent_zookeeper.sh",
            "tests/queries/0_stateless/00236_replicated_drop_on_non_leader_zookeeper_long.sql",
            "tests/queries/0_stateless/00215_primary_key_order_zookeeper_long.sql",
            "tests/queries/0_stateless/00083_create_merge_tree_zookeeper_long.sql",
        ]

        all_candidates = true_relevant + irrelevant

        results = filter_tests([changed_file], all_candidates)
        kept_paths = {path for path, _, _ in results}

        true_positives = len(true_relevant & kept_paths)
        false_positives = len(kept_paths - set(true_relevant))
        false_negatives = len(set(true_relevant) - kept_paths)

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0

        self.assertNotIn(
            "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh", kept_paths,
            "Pipeline UAF test must be filtered out for Keeper changes"
        )

        self.assertGreaterEqual(
            recall, 0.8,
            f"Recall must be >= 80%, got {recall:.1%}. "
            f"TP={true_positives}, FN={false_negatives}"
        )

        self.assertGreaterEqual(
            precision, 0.5,
            f"Precision must be >= 50%, got {precision:.1%}. "
            f"TP={true_positives}, FP={false_positives}"
        )


if __name__ == "__main__":
    unittest.main()
