import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def evaluate_release_checklist(root: Path, checklist: Dict[str, Any]) -> List[Dict[str, Any]]:
    readme_text = (root / "README.md").read_text(encoding="utf-8")
    results: List[Dict[str, Any]] = []

    for check in checklist["checks"]:
        status = False
        if check["kind"] == "path_exists":
            status = (root / check["path"]).exists()
        elif check["kind"] == "readme_contains":
            status = check["pattern"] in readme_text
        else:
            raise ValueError(f"Unsupported check kind: {check['kind']}")

        results.append(
            {
                "id": check["id"],
                "description": check["description"],
                "passed": status,
            }
        )

    return results


def analyze(root: Path) -> Dict[str, Any]:
    metadata_dir = root / "utils/repository-homepage"
    modules = load_json(metadata_dir / "homepage_modules.json")
    channels = load_json(metadata_dir / "community_channels.json")
    release_checklist = load_json(metadata_dir / "release_checklist.json")
    readme_text = (root / "README.md").read_text(encoding="utf-8")
    contributing_text = (root / "CONTRIBUTING.md").read_text(encoding="utf-8")

    release_results = evaluate_release_checklist(root, release_checklist)

    recommendations = [
        {
            "dimension": "文档与代码分离",
            "suggestion": "将首页里的安装入口与贡献导航沉淀为独立的工具链/文档元数据模块，让 README 只负责聚合入口而把实现归口到安装与文档仓库，可降低首页文案与交付脚本耦合并减少跨仓更新遗漏。",
        },
        {
            "dimension": "社区入口模块化",
            "suggestion": "把 README 中硬编码的 Slack、Telegram、Bluesky 与 X 链接抽离到独立社区配置文件，再由首页或站点生成逻辑统一消费，可把社区入口维护从文本编辑变成结构化配置更新并降低链接漂移风险。",
        },
        {
            "dimension": "发布流程脚本化",
            "suggestion": "把月度发布入口依赖的 README 节点、GitHub workflow、`tests/ci` 发布脚本与 changelog 目录收敛为可执行检查清单，可在发布前自动发现缺失项并把人工巡检流程压缩成一次脚本执行。",
        },
    ]

    snapshot = {
        "readme_has_install_snippet": "curl https://clickhouse.com/ | sh" in readme_text,
        "readme_has_monthly_release_section": "## Monthly Release & Community Call" in readme_text,
        "readme_has_community_links": all(
            channel["label"] in readme_text for channel in channels["channels"]
        ),
        "contributing_points_to_docs_repo": "documentation repository" in contributing_text,
        "module_count": len(modules["modules"]),
        "community_channel_count": len(channels["channels"]),
        "release_checks_passed": sum(1 for result in release_results if result["passed"]),
        "release_checks_total": len(release_results),
    }

    return {
        "snapshot": snapshot,
        "recommendations": recommendations,
        "release_checks": release_results,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    snapshot = report["snapshot"]
    lines = [
        f"- 仓库现状：README 仍同时承载安装、社区与月度发布入口，贡献说明则把深度文档导向外部文档仓库；当前发布检查通过 {snapshot['release_checks_passed']}/{snapshot['release_checks_total']}。",
    ]
    lines.extend(
        f"- {item['dimension']}：{item['suggestion']}" for item in report["recommendations"]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
    )
    parser.add_argument(
        "--check-release",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    report = analyze(root)

    if args.check_release:
        failed = [result for result in report["release_checks"] if not result["passed"]]
        if failed:
            print(json.dumps({"status": "failed", "checks": failed}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({"status": "ok", "checks": report["release_checks"]}, ensure_ascii=False, indent=2))
        return 0

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
