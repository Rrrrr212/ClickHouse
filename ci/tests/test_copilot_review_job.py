import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ci.jobs import copilot_review_job as review_job


class DummyInfo:
    pr_number = 123
    pr_url = "https://github.com/ClickHouse/ClickHouse/pull/123"
    repo_name = "ClickHouse/ClickHouse"

    def __init__(self, changed_files):
        self._changed_files = changed_files

    def get_changed_files(self):
        return self._changed_files


def test_infer_changed_file_module_for_clickhouse_core_areas():
    assert review_job._infer_changed_file_module("src/Parsers/ParserQuery.cpp") == "Parser"
    assert review_job._infer_changed_file_module("src/Storages/MergeTree/MergeTreeData.cpp") == "Storage"
    assert review_job._infer_changed_file_module("src/Functions/toString.cpp") == "Functions"
    assert review_job._infer_changed_file_module(
        "src/AggregateFunctions/AggregateFunctionSum.cpp"
    ) == "Aggregations"


def test_collect_review_focuses_flags_loops_allocations_and_serialization():
    focuses = review_job._collect_review_focuses(
        [
            "src/Functions/FunctionJSON.cpp",
            "src/AggregateFunctions/AggregateFunctionSum.cpp",
            "src/Storages/MergeTree/MergeTreeDataPartWriterWide.cpp",
        ]
    )

    assert any("Loops and vectorized paths" in focus for focus in focuses)
    assert any("Memory allocation and object lifetime" in focus for focus in focuses)
    assert any("Serialization and compatibility" in focus for focus in focuses)


def test_clickhouse_review_focus_contains_module_and_risk_hints():
    focus = review_job._clickhouse_review_focus(
        DummyInfo(
            [
                "src/Parsers/ParserQuery.cpp",
                "src/Storages/MergeTree/MergeTreeData.cpp",
                "src/Functions/toString.cpp",
            ]
        )
    )

    assert "`Parser`" in focus
    assert "`Storage`" in focus
    assert "`Functions`" in focus
    assert "integer overflow" in focus
    assert "use-after-free" in focus
    assert "iterator/reference invalidation" in focus


def test_pre_review_prompt_requires_markdown_table_output():
    prompt = review_job._pre_review_prompt(
        DummyInfo(
            [
                "src/Functions/toString.cpp",
                "src/AggregateFunctions/AggregateFunctionSum.cpp",
            ]
        )
    )

    assert "`风险等级 | 模块 | 文件位置 | 问题描述 | 修复建议`" in prompt
    assert "Performance-sensitive checks to prioritize" in prompt
    assert "ClickHouse-specific review acceleration" in prompt
