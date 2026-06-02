"""
AI-based automated PR code review job.

Two backends are supported, selected by flag:

  --codex    OpenAI Codex CLI       (auth: OPENAI_API_KEY from `/ci/llm/openai_api_key`)
  --copilot  GitHub Copilot CLI     (auth: gh robot token from `/ci/robot-ch-test-poll-copilot`)

Both agents shell out to `gh` to post inline review comments, so the gh CLI is
always authenticated against a temporary `GH_CONFIG_DIR` with the robot token
regardless of which backend runs the review itself.

The agent writes a free-form Markdown summary to `REVIEW_FILE`. The job script
then posts that summary via `python3 -m ci.praktika.gh post-or-update --tag review`
so the top-level comment is always authored by the pre-authenticated app, not
the agent's robot account.

Each agent occasionally hits transient GitHub authorization errors mid-run
("Authorization error, you may need to run /login"). The whole `gh auth` +
agent sequence is wrapped in a retry loop with exponential backoff so a single
transient API failure does not fail the Code Review job. Authorization-style
failures do not always surface as a Python exception — they show up as a
non-zero exit code and a missing/empty review file — so both are checked here.
"""

import os
import random
import shlex
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
from collections import defaultdict

from ci.praktika import Secret
from ci.praktika.info import Info
from ci.praktika.result import Result

REVIEW_FILE = "./ci/tmp/copilot_review.md"
GH_PREFIX = "env -u GH_CONFIG_DIR"

MAX_ATTEMPTS = 3

ROBOT_NAMES = [
    "/ci/robot-ch-test-poll-copilot",
    "/ci/robot-ch-test-poll-1-copilot",
]

OPENAI_KEY_SECRET = "/ci/llm/openai_api_key"

GENERIC_PATH_PARTS = {
    "src",
    "tests",
    "queries",
    "0_stateless",
    "0_stateful",
    "integration",
    "ci",
    "jobs",
    "scripts",
    "programs",
    "base",
    "docs",
    "utils",
    "tmp",
}

MODULE_NAME_MAP = {
    "AggregateFunctions": "Aggregations",
    "Analyzer": "Parser",
    "Columns": "Columns",
    "Common": "Core/Common",
    "Coordination": "Keeper/Coordination",
    "Core": "Core/Common",
    "Databases": "Storage",
    "Disks": "Storage",
    "Formats": "Formats",
    "Functions": "Functions",
    "Interpreters": "Interpreter/Planner",
    "Parsers": "Parser",
    "Processors": "Processors",
    "QueryPipeline": "Processors",
    "Storages": "Storage",
    "TableFunctions": "Functions",
}

MODULE_SPECIFIC_HINTS = {
    "Aggregations": [
        "trace aggregate-state layout, `Arena` lifetime, and `add`/`merge`/`serialize` symmetry",
        "check two-level aggregation, spill, and distributed merge paths",
    ],
    "Columns": [
        "look for implicit copies, missed `reserve`, and iterator/reference invalidation after inserts or resizes",
    ],
    "Formats": [
        "check schema/version compatibility, deterministic encoding, and unnecessary temporary buffers during I/O",
    ],
    "Functions": [
        "check vectorized execution on `ColumnConst`, `Nullable`, and `LowCardinality` inputs",
        "look for per-row allocations, repeated conversions, or branch-heavy work inside tight loops",
    ],
    "Interpreter/Planner": [
        "trace planner/executor invariants through settings, distributed execution, and fallback-free error paths",
    ],
    "Keeper/Coordination": [
        "check concurrency, ownership transfer, and metadata divergence after retries or failover",
    ],
    "Parser": [
        "check grammar ambiguity, AST/formatter round-trips, and compatibility with existing syntax",
    ],
    "Processors": [
        "check hot loops, chunk ownership, and pipeline backpressure or cancellation handling",
    ],
    "Storage": [
        "check part/metadata lifecycle, deletion logging, replication consistency, and exception safety under background work",
    ],
}

COMMON_RISK_HINTS = [
    "check integer overflow in `rows * bytes`, offsets, buffer growth, and signed/unsigned conversions; connect findings to the `No magic constants`, `Backward compatibility`, or `Core-area scrutiny` rules when relevant",
    "check use-after-free via `StringRef`, `Field`, `ColumnPtr`, temporary blocks, or async/background lambdas capturing references; connect findings to `Core-area scrutiny` or `Test coverage`",
    "check iterator/reference invalidation after `std::vector`/`PODArray` growth, hash-table rehash, or column mutation; connect findings to `Core-area scrutiny` and explain the concrete invalidation path",
]


class _ChangedFileAwareInfo:
    pr_number = 0
    pr_url = ""
    repo_name = ""

    def get_changed_files(self):
        return []


def _join_prompt(*sections):
    return "\n\n".join(section.rstrip() for section in sections if section).rstrip() + "\n"


def _repo_from_pr_url(pr_url):
    path_parts = urllib.parse.urlparse(pr_url).path.strip("/").split("/")
    if len(path_parts) >= 4 and path_parts[2] == "pull":
        return f"{path_parts[0]}/{path_parts[1]}"
    return ""


def _pr_repository(info):
    return _repo_from_pr_url(info.pr_url) or info.repo_name


def _normalize_changed_file_path(path):
    return path.removeprefix("./").replace("\\", "/")


def _module_from_path_component(component):
    return MODULE_NAME_MAP.get(component)


def _infer_changed_file_module(path):
    normalized = _normalize_changed_file_path(path)
    lower = normalized.lower()
    basename = lower.split("/")[-1]

    if "/aggregatefunctions/" in lower or "aggregatefunction" in basename:
        return "Aggregations"
    if "/functions/" in lower or "/tablefunctions/" in lower or basename.startswith("function"):
        return "Functions"
    if "/storages/" in lower or "/databases/" in lower or "/disks/" in lower or "test_storage_" in basename:
        return "Storage"
    if "/parsers/" in lower or "/analyzer/" in lower or basename.startswith("parser"):
        return "Parser"
    if "/formats/" in lower:
        return "Formats"
    if "/processors/" in lower or "/querypipeline/" in lower:
        return "Processors"
    if "/coordination/" in lower or "keeper" in lower:
        return "Keeper/Coordination"
    if "/interpreters/" in lower:
        return "Interpreter/Planner"
    if "/columns/" in lower:
        return "Columns"
    if "/core/" in lower or "/common/" in lower:
        return "Core/Common"

    for component in normalized.split("/"):
        mapped = _module_from_path_component(component)
        if mapped:
            return mapped

    for component in normalized.split("/"):
        if component and component not in GENERIC_PATH_PARTS:
            return component

    return "Cross-module"


def _collect_review_focuses(changed_files):
    normalized_files = [_normalize_changed_file_path(path) for path in changed_files]
    lowered = " ".join(path.lower() for path in normalized_files)
    modules = {_infer_changed_file_module(path) for path in normalized_files}
    focuses = []

    if modules & {
        "Aggregations",
        "Columns",
        "Formats",
        "Functions",
        "Interpreter/Planner",
        "Processors",
        "Storage",
    } or any(token in lowered for token in ("merge", "hash", "column", "vector", "loop", "chunk")):
        focuses.append(
            "Loops and vectorized paths: look for repeated virtual calls, redundant conversions, branch-heavy per-row work, missed `reserve`, and copies inside tight loops."
        )

    if modules & {
        "Aggregations",
        "Columns",
        "Core/Common",
        "Functions",
        "Storage",
    } or any(token in lowered for token in ("arena", "allocator", "memory", "cache", "column", "field", "block")):
        focuses.append(
            "Memory allocation and object lifetime: prioritize per-row allocations, reusable arenas/buffers, `StringRef` and `Field` lifetimes, and reallocation side effects on references or iterators."
        )

    if modules & {
        "Aggregations",
        "Formats",
        "Keeper/Coordination",
        "Parser",
        "Storage",
    } or any(token in lowered for token in ("serial", "format", "json", "native", "arrow", "proto", "keeper", "replicated")):
        focuses.append(
            "Serialization and compatibility: verify explicit versioning, deterministic encoding, upgrade/downgrade safety, and avoid repeated serialize/deserialize churn or temporary buffers in hot paths."
        )

    return focuses


def _module_hint_lines(changed_files):
    grouped = defaultdict(list)
    for path in changed_files:
        normalized = _normalize_changed_file_path(path)
        grouped[_infer_changed_file_module(normalized)].append(normalized)

    lines = []
    for module, files in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))[:8]:
        preview = ", ".join(f"`{path}`" for path in files[:3])
        suffix = "" if len(files) <= 3 else f", and {len(files) - 3} more"
        lines.append(f"- `{module}`: {preview}{suffix}")
    return lines


def _module_specific_hint_lines(changed_files):
    modules = []
    for path in changed_files:
        module = _infer_changed_file_module(path)
        if module not in modules:
            modules.append(module)

    lines = []
    for module in modules[:5]:
        hints = MODULE_SPECIFIC_HINTS.get(module)
        if hints:
            lines.append(f"- `{module}`: {'; '.join(hints)}")
    return lines


def _clickhouse_review_focus(info):
    changed_files = list(info.get_changed_files() or [])
    if not changed_files:
        return ""

    focus_lines = [
        "ClickHouse-specific review acceleration:",
        "- Auto-detected changed-file modules:",
        *_module_hint_lines(changed_files),
    ]

    performance_focuses = _collect_review_focuses(changed_files)
    if performance_focuses:
        focus_lines.append("- Performance-sensitive checks to prioritize:")
        focus_lines.extend(f"- {focus}" for focus in performance_focuses)

    module_hints = _module_specific_hint_lines(changed_files)
    if module_hints:
        focus_lines.append("- Module-specific invariants to trace:")
        focus_lines.extend(module_hints)

    focus_lines.append("- Common defect patterns to check explicitly:")
    focus_lines.extend(f"- {hint}" for hint in COMMON_RISK_HINTS)
    focus_lines.append(
        "- In every finding, state the affected module from the path-derived hints above. For cross-cutting findings, use `Cross-module`."
    )
    return "\n".join(focus_lines)


def _pre_review_instructions():
    return """\
Review instructions:
- Follow the Review Instructions in .claude/skills/review/SKILL.md.
- Repo is checked out at PR head.
- Post findings as individual inline review comments on specific lines.
"""


def _review_target(info):
    repo_name = _pr_repository(info)
    return f"""\
Review target:
- PR URL: {info.pr_url}
- PR repository: `{repo_name}`
- Always derive the PR repository from the PR URL or the CI event. For ClickHouse reviews this will be either
  `ClickHouse/ClickHouse` or `ClickHouse/ClickHouse-private`. Do not infer the review repository from
  the local checkout remote, because local checkouts may point to a fork.
"""


def _pre_review_tools(pr_number, repo_name):
    return f"""\
Tools:
- Prefix every `gh` call with `{GH_PREFIX}`.
- Pass `--repo {repo_name}` exactly as shown in each command below. For `gh` subcommands not shown
  here, only add `--repo` if the command documents it. Do NOT add `--repo` to
  `resolve-pr-review-thread` / `unresolve-pr-review-thread`: they take only `--thread-id` (a globally
  unique GraphQL node id that already identifies the repo) and reject `--repo` with
  `error: unrecognized arguments`.
- Post a new inline review comment by writing the body to a file and running:
  `{GH_PREFIX} python3 -m ci.praktika.gh post-pr-line-comment --file <body.md> --commit <sha> --path <file> --line <N> --repo {repo_name} [--side RIGHT|LEFT]`.
  This wrapper handles `-F body=@<file>` correctly so the file content is uploaded as the body.
- Do NOT call `gh api .../pulls/.../comments` directly: past runs have posted the literal `@<file>`
  string as the body when the wrong `gh` flag was used.
- Do NOT use `gh pr review`; that posts a single batched review, not individual line comments.
- Fetch inline review threads with:
  `{GH_PREFIX} python3 -m ci.praktika.gh list-pr-review-threads --pr {pr_number} --repo {repo_name}`.
  The command returns JSON; each thread carries its node `id`, `isResolved`, `resolvedBy.login`
  (the user who most recently resolved it, or `null`), `path`, `line`, and `comments.nodes` with
  author, body, `databaseId`, and `createdAt`.
- Fetch top-level conversation with:
  `{GH_PREFIX} gh api '/repos/{repo_name}/issues/{pr_number}/comments' --paginate`.
- Reply on an existing thread with:
  `{GH_PREFIX} python3 -m ci.praktika.gh post-pr-line-comment --file <body.md> --reply-to <parent_databaseId> --repo {repo_name}`.
  Use the `databaseId` of the first comment on the thread as `<parent_databaseId>`, and omit
  `--commit`, `--path`, and `--line`.
- Resolve or unresolve bot-authored review threads with:
  `{GH_PREFIX} python3 -m ci.praktika.gh resolve-pr-review-thread --thread-id <thread_node_id>`
  `{GH_PREFIX} python3 -m ci.praktika.gh unresolve-pr-review-thread --thread-id <thread_node_id>`.
"""


def _pre_review_procedure(pr_url):
    return f"""\
Procedure:
1. In GitHub discussions, "you" are the `clickhouse-gh` GitHub App. Its identity appears in two
   forms depending on which GraphQL field returns it: `clickhouse-gh` in `author.login` (comments,
   reviews) and `clickhouse-gh[bot]` in `resolvedBy.login` (review threads). Treat both as you.
2. Fetch all prior discussion on this PR before reviewing.
3. Provide a thorough review of {pr_url}. Read the current code and PR diff, not only the discussion.
4. Read every reply on every thread. Treat each reply as a deliberate engineering decision by the
   author. An explanation that holds up, a pointer to a fixing commit, or a tradeoff you agree with
   means drop the point. A dismissal ("no", "won't fix", "by design", "pathological", "wontfix",
   "agree to disagree", a silent thread resolution) is also a deliberate decision -- accept it. If
   you still believe the issue is real after the author's reply, see step 5 for what to do with it.
5. Apply the same judgment to your own prior summary: drop findings that have been addressed, keep
   or sharpen the rest. Verify by reading the current code, not by trusting the author's reply.
   Findings the author dismissed but you still consider real STAY in the summary's `Findings`
   section, marked `[dismissed by author -- <thread URL>]` with a one-line note on why you still
   consider it real. Do NOT migrate them back to the inline thread.
6. On existing threads, post a new comment only in these two cases:
   (a) The author asked you a direct, answerable question (e.g. "what would the fix look like?",
       "do you have a repro?"). Answer it once and stop -- do not restate the original finding.
   (b) The author explicitly claimed the issue is fixed ("fixed in <commit>", "this is fixed now")
       but the current code shows the original issue is still present. Reply once pointing to the
       `file:line` that disproves the claim. Distinguish this from a dismissal: "won't fix",
       "by design", "pathological", "no", a silent thread resolution are NOT fixed claims.
   In every other case, do not reply on the thread.
7. Resolve and re-open only threads you created yourself: that means threads whose first entry in
   `comments.nodes` has `author.login == "clickhouse-gh"`. Resolve such a thread when the issue no
   longer holds in the current code. Re-open such a thread only when it is resolved AND the issue
   is still present AND either:
   (a) the thread's `resolvedBy.login` is `"clickhouse-gh[bot]"` (whether you resolved it
       prematurely or a later commit reintroduced the issue). Re-open silently, no reply needed.
   (b) case 6(b) fires -- re-open AND post the 6(b) reply in the same run.
   Never resolve or unresolve threads whose first comment was authored by anyone else.
8. For genuinely new issues that do not already have a thread, post individual inline comments on the
   relevant changed lines. For architectural issues that do not map cleanly to one line, post around
   the most relevant change in the diff.
9. Do NOT post inline comments for issues that dedicated CI jobs already catch and report: build /
   compilation failures (missing headers, undeclared symbols, type errors, link errors) and style
   check failures (formatting, linters, `check_cpp.sh` / `check_style.sh` output). These are not
   blockers in this review context: the build and Style Check jobs surface them with full toolchain
   output, so a review comment is pure noise. If you want to mention them, include them only as
   `💡 Nits` in the summary file, never as inline comments or as `❌ Blockers` / `⚠️ Majors`.
"""


def _pre_review_output():
    return f"""\
Output:
Write a self-contained summary of ALL findings, regardless of previous summaries, as plain Markdown
to {REVIEW_FILE}. Keep the overall Summary / Findings / Final Verdict structure from
.claude/skills/review/SKILL.md, start with `---\n#### AI Review`, and use `#####` for section headers.
Render the `Findings` section as a Markdown table with the exact columns
`风险等级 | 模块 | 文件位置 | 问题描述 | 修复建议`.
- `风险等级` uses one of `❌ Blocker`, `⚠️ Major`, or `💡 Nit`.
- `模块` must be derived from the changed-file module hints in this prompt.
- `文件位置` uses `path:line` or `path:Lx-Ly` format.
- `问题描述` must mention the violated invariant, concrete impact, and when relevant cite the matching
  ClickHouse rule from `.claude/skills/review/SKILL.md`.
- `修复建议` must be concrete and may include a minimal patch or replacement code block.
When you see loops, allocations, or serialization changes in performance-sensitive code, prefer a
specific optimization suggestion over a generic warning.
Do NOT post the summary yourself: the job script will post it after you finish.
"""


def _pre_review_prompt(info):
    repo_name = _pr_repository(info)
    return _join_prompt(
        _pre_review_instructions(),
        _review_target(info),
        _pre_review_tools(info.pr_number, repo_name),
        _pre_review_procedure(info.pr_url),
        _clickhouse_review_focus(info),
        _pre_review_output(),
    )


def _reauth_gh():
    from ci.praktika.gh_auth import GHAuth

    GHAuth.auth_from_settings()


def _post_review():
    subprocess.run(
        [
            sys.executable, "-m", "ci.praktika.gh",
            "post-or-update", "--tag", "review", "--file", REVIEW_FILE,
        ],
        check=True,
    )


def _drop_stale_review_file():
    if os.path.exists(REVIEW_FILE):
        try:
            os.unlink(REVIEW_FILE)
        except OSError as e:
            print(f"WARNING: Failed to remove stale {REVIEW_FILE}: {e}")


def _gh_auth_with_robot_token(gh_config_dir, robot_name):
    print(f"Using robot: {robot_name}")
    token = Secret.Config(
        name=robot_name, type=Secret.Type.AWS_SSM_PARAMETER
    ).get_value()
    subprocess.run(
        ["gh", "auth", "login", "--with-token"],
        input=token, text=True, check=True,
        env={**os.environ, "GH_CONFIG_DIR": gh_config_dir},
    )


def _run_copilot_once(prompt, robot_name):
    _drop_stale_review_file()
    with tempfile.TemporaryDirectory() as gh_config_dir:
        _gh_auth_with_robot_token(gh_config_dir, robot_name)
        return Result.from_commands_run(
            name="copilot review",
            command=f"GH_CONFIG_DIR={shlex.quote(gh_config_dir)} "
                    f"copilot -p {shlex.quote(prompt)} --allow-all --no-ask-user "
                    f"--add-dir . --model gpt-5.5 --effort xhigh < /dev/null",
            with_info=True,
        )


def _run_codex_once(prompt, robot_name):
    _drop_stale_review_file()
    with tempfile.TemporaryDirectory() as gh_config_dir, \
         tempfile.TemporaryDirectory(dir="./ci/tmp") as codex_home:
        _gh_auth_with_robot_token(gh_config_dir, robot_name)

        openai_key = Secret.Config(
            name=OPENAI_KEY_SECRET, type=Secret.Type.AWS_SSM_PARAMETER
        ).get_value()
        subprocess.run(
            ["codex", "login", "--with-api-key"],
            input=openai_key, text=True, check=True,
            env={**os.environ, "CODEX_HOME": codex_home},
        )

        return Result.from_commands_run(
            name="codex review",
            command=f"CODEX_HOME={shlex.quote(codex_home)} "
                    f"GH_CONFIG_DIR={shlex.quote(gh_config_dir)} "
                    f"codex exec "
                    f"-m gpt-5.5 -c 'model_reasoning_effort=xhigh' "
                    f"-s workspace-write "
                    f"-c sandbox_workspace_write.network_access=true "
                    f"-c approval_policy=never "
                    f"--color never "
                    f"{shlex.quote(prompt)}",
            with_info=True,
        )


def _run(prompt, run_once, agent_name):
    last_error = None
    robots = ROBOT_NAMES.copy()
    random.shuffle(robots)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        robot_name = robots[(attempt - 1) % len(robots)]
        try:
            result = run_once(prompt, robot_name)
            if not result.is_ok():
                last_error = (
                    f"{agent_name} subprocess exited with non-OK status [{result.status}]"
                )
                print(f"WARNING: {agent_name} attempt {attempt}/{MAX_ATTEMPTS} failed: {last_error}")
            elif not os.path.exists(REVIEW_FILE):
                last_error = f"{agent_name} did not write {REVIEW_FILE}"
                print(f"WARNING: {agent_name} attempt {attempt}/{MAX_ATTEMPTS} failed: {last_error}")
            elif os.path.getsize(REVIEW_FILE) == 0:
                last_error = f"{REVIEW_FILE} is empty"
                print(f"WARNING: {agent_name} attempt {attempt}/{MAX_ATTEMPTS} failed: {last_error}")
            else:
                last_error = None
                break
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"WARNING: {agent_name} attempt {attempt}/{MAX_ATTEMPTS} raised: {last_error}")
            traceback.print_exc()

        if attempt < MAX_ATTEMPTS:
            delay = min(2 ** attempt, 60)
            print(f"Retrying {agent_name} in {delay}s ...")
            time.sleep(delay)

    if last_error is not None:
        raise RuntimeError(
            f"{agent_name} review failed after {MAX_ATTEMPTS} attempts: {last_error}"
        )

    _post_review()


def review(run_once, agent_name):
    info = Info()
    if not info.pr_number:
        print("Not a PR, skipping")
        return

    _reauth_gh()
    os.makedirs("./ci/tmp", exist_ok=True)
    prompt = _pre_review_prompt(info)
    _run(prompt, run_once, agent_name)


if __name__ == "__main__":
    if "--codex" in sys.argv:
        run_once, agent_name = _run_codex_once, "Codex"
    elif "--copilot" in sys.argv:
        run_once, agent_name = _run_copilot_once, "Copilot"
    else:
        print("Usage: copilot_review_job.py --codex | --copilot")
        sys.exit(1)

    status = Result.Status.OK
    info = ""
    try:
        review(run_once, agent_name)
    except Exception as e:
        info = f"ERROR: {e}"
        print(info)
        traceback.print_exc()
        status = Result.Status.FAIL

    Result.create_from(status=status, info=info).complete_job()
