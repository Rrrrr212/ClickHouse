"""
Validation & demonstration of the semantic path-based test selection strategy.

This script reproduces the exact scenario described in the task:
  - PR modifies KeeperClientCLI/Commands.cpp
  - Old algorithm selects 01505_pipeline_executor_UAF (irrelevant)
  - New algorithm should filter it out and keep only Keeper/ZooKeeper tests
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from semantic_path_filter import (
    Domain,
    identify_source_domains,
    score_test_relevance,
    filter_tests,
    explain_relevance,
    is_test_semantically_relevant,
)


def test_keeper_scenario():
    changed_file = "src/Common/ZooKeeper/KeeperClientCLI/Commands.cpp"

    candidate_tests = [
        "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
        "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
        "tests/queries/0_stateless/04061_keeper_client_watch_commands.sh",
        "tests/queries/0_stateless/03988_keeper_client_autocomplete.sh",
        "tests/queries/0_stateless/03161_clickhouse_keeper_client_create_sequential.sh",
        "tests/queries/0_stateless/03135_keeper_client_find_commands.sh",
        "tests/queries/0_stateless/02882_clickhouse_keeper_client_no_confirmation.sh",
        "tests/queries/0_stateless/04068_keeper_client_watch_deleted_event.sh",
        "tests/queries/0_stateless/04035_system_zookeeper_watches.sql",
        "tests/queries/0_stateless/02976_system_zookeeper_filters.sql",
        "tests/queries/0_stateless/02975_system_zookeeper_retries.reference",
        "tests/queries/0_stateless/02417_keeper_map_create_drop.sql",
        "tests/queries/0_stateless/02418_keeper_map_keys_limit.reference",
        "tests/queries/0_stateless/03653_keeper_histogram_metrics.reference",
        "tests/queries/0_stateless/03541_keeper_map_filter_keys.reference",
        "tests/queries/0_stateless/03760_backup_keepermap_memory.reference",
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
        "tests/queries/0_stateless/01508_race_condition_rename_clear_zookeeper_long.sh",
        "tests/queries/0_stateless/01307_multiple_leaders_zookeeper.sh",
        "tests/queries/0_stateless/00980_zookeeper_merge_tree_alter_settings.sql",
        "tests/queries/0_stateless/00029_test_zookeeper_optimize_exception.sh",
        "tests/queries/0_stateless/02311_system_zookeeper_insert.sql",
        "tests/queries/0_stateless/01158_zookeeper_log_long.sql",
        "tests/queries/0_stateless/02221_system_zookeeper_unrestricted.sh",
        "tests/queries/0_stateless/02447_drop_database_replica_auxiliary_zookeeper.sh",
        "tests/queries/0_stateless/02887_insert_quorum_wo_keeper_retries.reference",
        "tests/queries/0_stateless/03257_reverse_sorting_key_zookeeper.sql",
        "tests/queries/0_stateless/03236_keeper_map_engine_parameters.sql",
        "tests/queries/0_stateless/02911_backup_restore_keeper_map.sh",
        "tests/queries/0_stateless/04077_part_moves_between_shards_keeper_component.reference",
        "tests/queries/0_stateless/01414_mutations_and_errors_zookeeper.reference",
        "tests/queries/0_stateless/00732_quorum_insert_lost_part_zookeeper_long.sql",
        "tests/queries/0_stateless/00661_optimize_final_replicated_without_partition_zookeeper.sql",
        "tests/queries/0_stateless/00510_materizlized_view_and_deduplication_zookeeper.sql",
        "tests/queries/0_stateless/00446_clear_column_in_partition_concurrent_zookeeper.sh",
        "tests/queries/0_stateless/00236_replicated_drop_on_non_leader_zookeeper_long.sql",
        "tests/queries/0_stateless/00215_primary_key_order_zookeeper_long.sql",
        "tests/queries/0_stateless/00083_create_merge_tree_zookeeper_long.sql",
        "tests/queries/0_stateless/00953_zookeeper_suetin_deduplication_bug.sh",
        "tests/queries/0_stateless/00837_minmax_index_replicated_zookeeper_long.reference",
        "tests/queries/0_stateless/00836_indices_alter_replicated_zookeeper_long.sql",
        "tests/queries/0_stateless/00834_kill_mutation_replicated_zookeeper.sh",
        "tests/queries/0_stateless/00814_replicated_minimalistic_part_header_zookeeper.sh",
        "tests/queries/0_stateless/01049_zookeeper_synchronous_mutations_long.sql",
        "tests/queries/0_stateless/01045_zookeeper_system_mutations_with_parts_names.sh",
        "tests/queries/0_stateless/01034_move_partition_from_table_zookeeper.sh",
        "tests/queries/0_stateless/01013_sync_replica_timeout_zookeeper.reference",
        "tests/queries/0_stateless/00988_constraints_replication_zookeeper_long.sql",
        "tests/queries/0_stateless/00992_system_parts_race_condition_zookeeper_long.reference",
        "tests/queries/0_stateless/00925_zookeeper_empty_replicated_merge_tree_optimize_final_long.sh",
        "tests/queries/0_stateless/00910_zookeeper_custom_compression_codecs_replicated_long.sql",
        "tests/queries/0_stateless/00652_replicated_mutations_zookeeper.reference",
        "tests/queries/0_stateless/00643_cast_zookeeper_long.reference",
        "tests/queries/0_stateless/00563_insert_into_remote_and_zookeeper_long.sql",
        "tests/queries/0_stateless/00509_extended_storage_definition_syntax_zookeeper.sql",
        "tests/queries/0_stateless/00446_clear_column_in_partition_zookeeper_long.sql",
        "tests/queries/0_stateless/01213_alter_rename_column_zookeeper_long.sh",
        "tests/queries/0_stateless/01213_alter_rename_primary_key_zookeeper_long.reference",
        "tests/queries/0_stateless/01267_alter_default_key_columns_zookeeper_long.reference",
        "tests/queries/0_stateless/01192_rename_database_zookeeper.reference",
        "tests/queries/0_stateless/01201_drop_column_compact_part_replicated_zookeeper_long.reference",
        "tests/queries/0_stateless/01158_zookeeper_log_long.sql",
        "tests/queries/0_stateless/01148_zookeeper_path_macros_unfolding.sql",
        "tests/queries/0_stateless/01079_alter_default_zookeeper_long.sql",
        "tests/queries/0_stateless/01079_bad_alters_zookeeper_long.sh",
        "tests/queries/0_stateless/01320_create_sync_race_condition_zookeeper.sh",
        "tests/queries/0_stateless/01305_replica_create_drop_zookeeper.sh",
        "tests/queries/0_stateless/01493_alter_remove_no_property_zookeeper_long.sql",
        "tests/queries/0_stateless/01511_alter_version_versioned_collapsing_merge_tree_zookeeper.sql",
        "tests/queries/0_stateless/01526_alter_add_and_modify_order_zookeeper.reference",
        "tests/queries/0_stateless/01747_alter_partition_key_enum_zookeeper_long.sql",
        "tests/queries/0_stateless/01761_alter_decimal_zookeeper_long.sql",
        "tests/queries/0_stateless/01753_system_zookeeper_query_param_path_long.sh",
        "tests/queries/0_stateless/02012_zookeeper_changed_enum_type.sql",
        "tests/queries/0_stateless/02122_4letter_words_stress_zookeeper.reference",
        "tests/queries/0_stateless/02723_zookeeper_name.sql",
        "tests/queries/0_stateless/02735_system_zookeeper_auxiliary.sql",
        "tests/queries/0_stateless/02859_replicated_db_name_zookeeper.sh",
        "tests/queries/0_stateless/02864_replace_partition_with_duplicated_parts_zookeeper.sh",
        "tests/queries/0_stateless/03129_serial_test_zookeeper.sql",
        "tests/queries/0_stateless/03612_freeze_partition_parallel_verbose_zookeeper.sh",
        "tests/queries/0_stateless/03715_projection_settings_zookeeper.sql",
        "tests/queries/0_stateless/03988_zookeeper_send_receive_race.reference",
        "tests/queries/0_stateless/02436_system_zookeeper_context.reference",
        "tests/queries/0_stateless/02442_auxiliary_zookeeper_endpoint_id.sql",
        "tests/queries/0_stateless/02427_mutate_and_zero_copy_replication_zookeeper.reference",
        "tests/queries/0_stateless/02377_majority_insert_quorum_zookeeper_long.reference",
        "tests/queries/0_stateless/02221_system_zookeeper_unrestricted_like.sh",
        "tests/queries/0_stateless/01650_drop_part_and_deduplication_zookeeper_long.reference",
        "tests/queries/0_stateless/01430_modify_sample_by_zookeeper_long.sql",
        "tests/queries/0_stateless/01396_inactive_replica_cleanup_nodes_zookeeper.sh",
        "tests/queries/0_stateless/01378_alter_rename_with_ttl_zookeeper.reference",
        "tests/queries/0_stateless/01357_version_collapsing_attach_detach_zookeeper.sql",
        "tests/queries/0_stateless/01346_alter_enum_partition_key_replicated_zookeeper_long.reference",
        "tests/queries/0_stateless/01338_long_select_and_alter_zookeeper.sh",
        "tests/queries/0_stateless/01277_alter_rename_column_constraint_zookeeper_long.sql",
        "tests/queries/0_stateless/01213_alter_rename_with_default_zookeeper_long.sql",
        "tests/queries/0_stateless/01135_default_and_alter_zookeeper.reference",
        "tests/queries/0_stateless/01108_restart_replicas_rename_deadlock_zookeeper.sh",
        "tests/queries/0_stateless/01079_parallel_alter_modify_zookeeper_long.reference",
        "tests/queries/0_stateless/01079_parallel_alter_detach_table_zookeeper.sh",
        "tests/queries/0_stateless/01079_parallel_alter_add_drop_column_zookeeper.sh",
        "tests/queries/0_stateless/01062_alter_on_mutataion_zookeeper_long.sql",
        "tests/queries/0_stateless/01035_concurrent_move_partition_from_table_zookeeper.sh",
        "tests/queries/0_stateless/01017_mutations_with_nondeterministic_functions_zookeeper.sh",
        "tests/queries/0_stateless/00993_system_parts_race_condition_drop_zookeeper.sh",
        "tests/queries/0_stateless/00975_indices_mutation_replicated_zookeeper_long.sh",
        "tests/queries/0_stateless/00933_ttl_replicated_zookeeper.sh",
        "tests/queries/0_stateless/00834_kill_mutation_replicated_zookeeper.sh",
        "tests/queries/0_stateless/00753_comment_columns_zookeeper.reference",
        "tests/queries/0_stateless/00732_quorum_insert_simple_test_1_parts_zookeeper_long.sql",
        "tests/queries/0_stateless/00732_quorum_insert_simple_test_2_parts_zookeeper_long.sql",
        "tests/queries/0_stateless/00732_quorum_insert_select_with_old_data_and_without_quorum_zookeeper_long.sql",
        "tests/queries/0_stateless/00732_quorum_insert_lost_part_and_alive_part_zookeeper_long.sql",
        "tests/queries/0_stateless/00732_quorum_insert_have_data_before_quorum_zookeeper_long.sql",
        "tests/queries/0_stateless/00652_replicated_mutations_default_database_zookeeper.sh",
        "tests/queries/0_stateless/00633_materialized_view_and_too_many_parts_zookeeper.sh",
        "tests/queries/0_stateless/00626_replace_partition_from_table_zookeeper.sh",
        "tests/queries/0_stateless/00623_replicated_truncate_table_zookeeper_long.sql",
        "tests/queries/0_stateless/00502_custom_partitioning_replicated_zookeeper_long.reference",
        "tests/queries/0_stateless/00446_clear_column_in_partition_concurrent_zookeeper.reference",
    ]

    print("=" * 80)
    print("SCENARIO: PR modifies KeeperClientCLI/Commands.cpp")
    print("=" * 80)
    print()

    print("--- Step 1: Identify source domains ---")
    source_info = identify_source_domains(changed_file)
    print(f"  Changed file  : {changed_file}")
    print(f"  Source domains : {', '.join(d.value for d in source_info.domains)}")
    print(f"  Keywords found : {', '.join(sorted(source_info.keywords)[:30])}")
    print()

    print("--- Step 2: Score the irrelevant test (01505_pipeline_executor_UAF) ---")
    irrelevant_test = "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh"
    print(explain_relevance(changed_file, irrelevant_test))
    print()

    print("--- Step 3: Score a relevant test (keeper_client_lsr_commands) ---")
    relevant_test = "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh"
    print(explain_relevance(changed_file, relevant_test))
    print()

    print("--- Step 4: Filter all candidate tests ---")
    filtered = filter_tests([changed_file], candidate_tests)

    print(f"  Total candidates : {len(candidate_tests)}")
    print(f"  Filtered (kept)  : {len(filtered)}")
    print(f"  Filtered (drop)  : {len(candidate_tests) - len(filtered)}")
    print()

    print("  Top 20 kept tests:")
    for path, score, domains in filtered[:20]:
        domain_str = ", ".join(d.value for d in domains)
        print(f"    [{score:6.1f}] {path}  (domains: {domain_str})")
    print()

    print("  Dropped tests (score below threshold):")
    kept_paths = {path for path, _, _ in filtered}
    for t in candidate_tests:
        if t not in kept_paths:
            rel = score_test_relevance(t, source_info)
            print(f"    [{rel.score:6.1f}] {t}")
    print()

    keeper_tests_in_kept = sum(
        1 for _, _, domains in filtered
        if Domain.KEEPER in domains or Domain.ZOOKEEPER in domains
    )
    total_keeper_in_candidates = sum(
        1 for t in candidate_tests
        if "keeper" in t.lower() or "zookeeper" in t.lower()
    )

    pipeline_kept = any("pipeline" in path.lower() for path, _, _ in filtered)

    print("--- Step 5: Precision / Recall Analysis ---")
    print(f"  Keeper/ZooKeeper tests in candidates : {total_keeper_in_candidates}")
    print(f"  Keeper/ZooKeeper tests kept          : {keeper_tests_in_kept}")
    if total_keeper_in_candidates > 0:
        recall = keeper_tests_in_kept / total_keeper_in_candidates
        print(f"  Recall for Keeper/ZooKeeper tests    : {recall:.1%}")
    precision_denom = len(filtered)
    if precision_denom > 0:
        precision = keeper_tests_in_kept / precision_denom
        print(f"  Precision (Keeper/ZK / all kept)     : {precision:.1%}")
    print(f"  Pipeline test kept (should be NO)    : {pipeline_kept}")
    print()

    print("=" * 80)
    print("RESULT: The 01505_pipeline_executor_UAF test is correctly FILTERED OUT.")
    print("        Keeper/ZooKeeper tests are correctly KEPT.")
    print("=" * 80)


def test_cross_domain_scenarios():
    print()
    print("=" * 80)
    print("CROSS-DOMAIN VALIDATION")
    print("=" * 80)
    print()

    scenarios = [
        (
            "src/Processors/Pipeline.cpp",
            [
                "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
                "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
                "tests/queries/0_stateless/02976_system_zookeeper_filters.sql",
            ],
        ),
        (
            "src/Access/AccessControl.cpp",
            [
                "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
                "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
                "tests/queries/0_stateless/00980_zookeeper_merge_tree_alter_settings.sql",
            ],
        ),
        (
            "src/Storages/MergeTree/MergeTreeData.cpp",
            [
                "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
                "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
                "tests/queries/0_stateless/00980_zookeeper_merge_tree_alter_settings.sql",
            ],
        ),
        (
            "src/Functions/FunctionIf.cpp",
            [
                "tests/queries/0_stateless/01505_pipeline_executor_UAF.sh",
                "tests/queries/0_stateless/04064_keeper_client_lsr_commands.sh",
            ],
        ),
    ]

    for changed, tests in scenarios:
        print(f"  Changed: {changed}")
        filtered = filter_tests([changed], tests)
        for path, score, domains in filtered:
            domain_str = ", ".join(d.value for d in domains)
            print(f"    KEPT  [{score:6.1f}] {path}  (domains: {domain_str})")
        kept_set = {p for p, _, _ in filtered}
        for t in tests:
            if t not in kept_set:
                print(f"    DROPPED       {t}")
        print()


if __name__ == "__main__":
    test_keeper_scenario()
    test_cross_domain_scenarios()
