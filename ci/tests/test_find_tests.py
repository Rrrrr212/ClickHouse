"""
Regression tests for `ci/jobs/scripts/find_tests.py` test-name derivation.

PR #104097 changed only `tests/queries/0_stateless/02995_settings_26_4_1.tsv`
under `tests/queries/0_stateless/`.  The flaky-check driver derived the test
name `02995_settings_26_4_1` by stripping the extension and asked
`clickhouse-test` to re-run it 50 times — but no test with that base name
exists (the `.tsv` is a data file consumed by `02995_new_settings_history.sh`).
The filter matched zero tests and `clickhouse-test` exited with code 1.

These tests pin the corrected behaviour: orphan supporting files are skipped,
and supporting files with a real sibling test (e.g. `.reference`) still map
back to that test.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ci.jobs.scripts.find_tests import Targeting


def test_orphan_data_file_is_skipped():
    # PR #104097 reproducer: a `.tsv` data file consumed by another test.
    assert (
        Targeting._derive_test_name(
            "tests/queries/0_stateless/02995_settings_26_4_1.tsv"
        )
        is None
    )


def test_test_source_files_keep_base_name():
    assert (
        Targeting._derive_test_name(
            "tests/queries/0_stateless/02995_new_settings_history.sh"
        )
        == "02995_new_settings_history"
    )
    assert (
        Targeting._derive_test_name(
            "tests/queries/0_stateless/02995_index_1.sql"
        )
        == "02995_index_1"
    )
    assert (
        Targeting._derive_test_name(
            "tests/queries/0_stateless/00172_hits_joins.sql.j2"
        )
        == "00172_hits_joins"
    )


def test_reference_file_maps_to_sibling_test():
    # `.reference` for a sibling `.sh`.
    assert (
        Targeting._derive_test_name(
            "tests/queries/0_stateless/02995_new_settings_history.reference"
        )
        == "02995_new_settings_history"
    )
    # `.reference.j2` for a sibling `.sql.j2`.
    assert (
        Targeting._derive_test_name(
            "tests/queries/0_stateless/00172_hits_joins.reference.j2"
        )
        == "00172_hits_joins"
    )


def test_unknown_data_file_with_no_sibling_is_skipped():
    assert (
        Targeting._derive_test_name(
            "tests/queries/0_stateless/99999_no_such_test.tsv"
        )
        is None
    )


# ---------------------------------------------------------------------------
# Domain-relevance scoring tests
# ---------------------------------------------------------------------------


class TestExtractPathDomainKeywords:
    def test_keeper_zookeeper_path(self):
        kws = Targeting._extract_path_domain_keywords(
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"
        )
        kw_lower = {k.lower() for k in kws}
        assert "keeper" in kw_lower, (
            f"Expected 'keeper' in keywords from KeeperClientCLI path, got {kws}"
        )
        assert "zoo" in kw_lower, (
            f"Expected 'zoo' in keywords from ZooKeeper path, got {kws}"
        )

    def test_parquet_path(self):
        kws = Targeting._extract_path_domain_keywords(
            "src/Processors/Formats/Impl/Parquet/ParquetDecoding.cpp"
        )
        kw_lower = {k.lower() for k in kws}
        assert "parquet" in kw_lower, (
            f"Expected 'parquet' in keywords, got {kws}"
        )

    def test_arrow_path(self):
        kws = Targeting._extract_path_domain_keywords(
            "src/Processors/Formats/Impl/ArrowColumnToCHColumn.cpp"
        )
        kw_lower = {k.lower() for k in kws}
        assert "arrow" in kw_lower, (
            f"Expected 'arrow' in keywords, got {kws}"
        )

    def test_generic_path_returns_empty(self):
        kws = Targeting._extract_path_domain_keywords(
            "src/Common/ThreadPool.cpp"
        )
        assert len(kws) == 0, (
            f"Expected empty keywords for generic path, got {kws}"
        )

    def test_storages_path_returns_empty(self):
        kws = Targeting._extract_path_domain_keywords(
            "src/Storages/MergeTree/MergeTreeData.cpp"
        )
        assert len(kws) == 0, (
            f"Expected empty keywords for MergeTree path, got {kws}"
        )


class TestComputeDomainRelevance:
    def test_keeper_test_matches_keeper_keywords(self):
        dr = Targeting._compute_domain_relevance(
            "04068_keeper_client_watch_deleted_event",
            ["Zoo", "Keeper", "KeeperClientCLI", "Commands"],
        )
        assert dr > 1.0, (
            f"Expected boost for keeper test, got {dr}"
        )

    def test_unrelated_test_penalized(self):
        dr = Targeting._compute_domain_relevance(
            "01505_pipeline_executor_UAF",
            ["Zoo", "Keeper", "KeeperClientCLI", "Commands"],
        )
        assert dr < 1.0, (
            f"Expected penalty for unrelated test, got {dr}"
        )

    def test_unrelated_test_score_is_0_35(self):
        dr = Targeting._compute_domain_relevance(
            "01505_pipeline_executor_UAF",
            ["Zoo", "Keeper", "KeeperClientCLI", "Commands"],
        )
        assert dr == 0.35, (
            f"Expected 0.35 penalty for unrelated test, got {dr}"
        )

    def test_multiple_keyword_match_gives_higher_boost(self):
        dr1 = Targeting._compute_domain_relevance(
            "04068_keeper_client_watch_deleted_event",
            ["Zoo", "Keeper", "KeeperClientCLI", "Commands"],
        )
        dr2 = Targeting._compute_domain_relevance(
            "04064_keeper_client_lsr_commands",
            ["Zoo", "Keeper", "KeeperClientCLI", "Commands"],
        )
        assert dr2 > dr1, (
            f"2-keyword match should score higher than 1-keyword, got {dr2} <= {dr1}"
        )

    def test_no_keywords_returns_neutral(self):
        dr = Targeting._compute_domain_relevance(
            "01505_pipeline_executor_UAF",
            [],
        )
        assert dr == 1.0, (
            f"Expected neutral 1.0 when no keywords, got {dr}"
        )

    def test_zookeeper_test_matches(self):
        dr = Targeting._compute_domain_relevance(
            "03988_zookeeper_send_receive_race",
            ["Zoo", "Keeper", "KeeperClientCLI", "Commands"],
        )
        assert dr > 1.0, (
            f"Expected boost for zookeeper test, got {dr}"
        )


class TestDomainRelevanceIntegration:
    """
    End-to-end test: given a PR that only changes KeeperClientCLI/Commands.cpp,
    verify that Keeper-related tests are boosted and unrelated tests like
    pipeline_executor_UAF are penalized below the ranking threshold.

    This simulates the scenario described in the original bug report:
    - Old algorithm selects 01505_pipeline_executor_UAF (precision ≈ 50%)
    - New algorithm with domain-relevance scoring should exclude it
    - Target: precision > 80%
    """
    def test_keeper_change_boosts_keeper_tests(self):
        keeper_kws = Targeting._extract_path_domain_keywords(
            "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"
        )
        assert len(keeper_kws) > 0, "Should have domain keywords for Keeper path"

        keeper_test = "04068_keeper_client_watch_deleted_event"
        unrelated_test = "01505_pipeline_executor_UAF"

        dr_keeper = Targeting._compute_domain_relevance(keeper_test, keeper_kws)
        dr_unrelated = Targeting._compute_domain_relevance(unrelated_test, keeper_kws)

        assert dr_keeper > 1.0, f"Keeper test should be boosted, got {dr_keeper}"
        assert dr_unrelated == 0.35, f"Unrelated test should be penalized, got {dr_unrelated}"

        relative_ratio = dr_keeper / dr_unrelated
        assert relative_ratio > 3.0, (
            f"Boosted test should have at least 3x the score of penalized test, "
            f"got ratio {relative_ratio:.2f}"
        )

    def test_no_penalty_when_no_domain_signal(self):
        generic_kws = Targeting._extract_path_domain_keywords(
            "src/Common/ThreadPool.cpp"
        )
        assert len(generic_kws) == 0, "No domain keywords for generic path"

        dr = Targeting._compute_domain_relevance("01505_pipeline_executor_UAF", generic_kws)
        assert dr == 1.0, (
            f"Should be neutral when no domain signal, got {dr}"
        )
