#!/usr/bin/env python3
"""
ClickHouse Monthly Release Checklist Executor

Converts the release checklist from a static document into an executable,
trackable script that validates each step of the release process.

Usage:
    python3 tools/release/release_checklist.py --month 2026-06
    python3 tools/release/release_checklist.py --month 2026-06 --phase pre_release
    python3 tools/release/release_checklist.py --validate
    python3 tools/release/release_checklist.py --report
    python3 tools/release/release_checklist.py --month 2026-06 --mark-complete tag_release  # noqa

State Management:
    - Checklist progress is stored in tools/release/.state/YYYY-MM.json
    - Each checklist item tracks: completed, timestamp, output, notes
"""

import argparse
import datetime
import json
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

SCRIPT_DIR = Path(__file__).parent
STATE_DIR = SCRIPT_DIR / ".state"

CHECKLIST_CONFIG = SCRIPT_DIR / "release_checklist.yaml"

COLOR_RED = "\033[0;31m"
COLOR_GREEN = "\033[0;32m"
COLOR_YELLOW = "\033[1;33m"
COLOR_BLUE = "\033[0;34m"
COLOR_CYAN = "\033[0;36m"
COLOR_RESET = "\033[0m"


class ChecklistItem:
    def __init__(self, item_id: str, data: Dict):
        self.id = item_id
        self.name = data.get("name", item_id)
        self.description = data.get("description", "")
        self.automated = data.get("automated", False)
        self.check_command = data.get("check_command", "")
        self.manual_steps = data.get("manual_steps", [])
        self.completed = False
        self.timestamp = None
        self.output = ""
        self.notes = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "completed": self.completed,
            "timestamp": self.timestamp,
            "output": self.output,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ChecklistItem":
        item = cls(data["id"], data)
        item.completed = data.get("completed", False)
        item.timestamp = data.get("timestamp")
        item.output = data.get("output", "")
        item.notes = data.get("notes", "")
        return item


class ReleasePhase:
    def __init__(self, phase_id: str, data: Dict):
        self.id = phase_id
        self.name = data.get("name", phase_id)
        self.order = data.get("order", 0)
        self.responsible = data.get("responsible", "")
        self.items: List[ChecklistItem] = []

        for item_data in data.get("checklist", []):
            item = ChecklistItem(item_data["id"], item_data)
            self.items.append(item)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ReleasePhase":
        phase = cls(data["id"], data)
        phase.items = [ChecklistItem.from_dict(item) for item in data.get("items", [])]
        return phase


def load_checklist_config() -> Dict:
    with open(CHECKLIST_CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_state_file(month: str) -> Path:
    return STATE_DIR / f"{month}.json"


def load_state(month: str) -> Optional[Dict]:
    state_file = get_state_file(month)
    if not state_file.exists():
        return None
    with open(state_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(month: str, state: Dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = get_state_file(month)
    state["last_updated"] = datetime.datetime.now().isoformat()
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def init_state(month: str, config: Dict) -> Dict:
    state = {
        "month": month,
        "created_at": datetime.datetime.now().isoformat(),
        "last_updated": datetime.datetime.now().isoformat(),
        "phases": [],
    }
    for phase_data in config.get("phases", []):
        phase = ReleasePhase(phase_data["id"], phase_data)
        state["phases"].append(phase.to_dict())
    return state


def run_automated_check(item: ChecklistItem, variables: Dict) -> Tuple[bool, str]:
    command = item.check_command
    for key, value in variables.items():
        command = command.replace("{" + key + "}", str(value))

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=SCRIPT_DIR.parent.parent,
        )
        output = result.stdout.strip() + "\n" + result.stderr.strip()
        success = result.returncode == 0
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 300 seconds"
    except Exception as e:
        return False, f"Error executing command: {e}"


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{COLOR_RESET}"


def print_status_icon(completed: bool) -> str:
    if completed:
        return colorize("✓", COLOR_GREEN)
    return colorize("✗", COLOR_RED)


def print_report(state: Dict) -> None:
    total_items = 0
    completed_items = 0

    for phase_data in state.get("phases", []):
        phase = ReleasePhase.from_dict(phase_data)
        phase_completed = sum(1 for item in phase.items if item.completed)
        phase_total = len(phase.items)
        total_items += phase_total
        completed_items += phase_completed

        icon = "✓" if phase_completed == phase_total else " "
        print(f"\n{colorize(f'[{icon}] Phase {phase.order}: {phase.name}', COLOR_CYAN)}")
        print(f"  Responsible: {phase.responsible}")
        print(f"  Progress: {phase_completed}/{phase_total}")

        for item in phase.items:
            status = print_status_icon(item.completed)
            auto_label = colorize("[AUTO]", COLOR_BLUE) if item.automated else "[MANUAL]"
            print(f"    {status} {auto_label} {item.name}")
            if item.notes:
                print(f"        Notes: {item.notes}")
            if item.timestamp:
                print(f"        Completed: {item.timestamp}")

    print(f"\n{colorize('=== Overall Progress ===', COLOR_CYAN)}")
    print(f"Total: {completed_items}/{total_items} items completed")

    if completed_items == total_items:
        print(colorize("\nAll checklist items completed! Ready for release. ✓", COLOR_GREEN))
    else:
        remaining = total_items - completed_items
        print(colorize(f"\n{remaining} items remaining. Keep going!", COLOR_YELLOW))


def execute_checklist(state: Dict, variables: Dict, phase_filter: Optional[str] = None) -> None:
    for phase_data in state.get("phases", []):
        if phase_filter and phase_data["id"] != phase_filter:
            continue

        phase = ReleasePhase.from_dict(phase_data)
        print(f"\n{colorize(f'Phase {phase.order}: {phase.name}', COLOR_CYAN)}")
        print(f"  Responsible: {phase.responsible}")
        print()

        for item in phase.items:
            if item.completed:
                print(f"  {print_status_icon(True)} {item.name} (already completed)")
                continue

            print(f"  {colorize('▶', COLOR_YELLOW)} {item.name}")
            print(f"    {item.description}")

            if item.automated and item.check_command:
                print(f"    {colorize('Running automated check...', COLOR_BLUE)}")
                success, output = run_automated_check(item, variables)
                item.completed = success
                item.timestamp = datetime.datetime.now().isoformat()
                item.output = output

                if success:
                    print(f"    {print_status_icon(True)} Passed")
                else:
                    print(f"    {print_status_icon(False)} Failed")
                    if output:
                        print(f"    Output: {output[:500]}")
            elif item.manual_steps:
                print(f"    {colorize('Manual steps required:', COLOR_YELLOW)}")
                for step in item.manual_steps:
                    print(f"      - {step}")
                print()
                response = input(f"    Mark as complete? (y/n): ").strip().lower()
                if response == "y":
                    item.completed = True
                    item.timestamp = datetime.datetime.now().isoformat()
                    notes = input(f"    Add notes (optional): ").strip()
                    if notes:
                        item.notes = notes
                else:
                    notes = input(f"    Add notes (optional): ").strip()
                    if notes:
                        item.notes = notes

            # Update phase data
            phase_data["items"] = [item.to_dict() for item in phase.items]


def validate_config() -> bool:
    try:
        config = load_checklist_config()
    except Exception as e:
        print(f"Error loading checklist config: {e}")
        return False

    errors = []
    for phase in config.get("phases", []):
        if "id" not in phase:
            errors.append(f"Phase missing 'id': {phase.get('name', 'unknown')}")
        if "checklist" not in phase:
            errors.append(f"Phase '{phase.get('id', 'unknown')}' missing 'checklist'")

        for item in phase.get("checklist", []):
            if "id" not in item:
                errors.append(f"Item in '{phase.get('id')}' missing 'id'")
            if item.get("automated") and not item.get("check_command"):
                errors.append(
                    f"Automated item '{item.get('id')}' in '{phase.get('id')}' "
                    f"missing 'check_command'"
                )

    if errors:
        print("Configuration validation FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("Configuration validation PASSED")
    print(f"Phases: {len(config.get('phases', []))}")
    total_items = sum(
        len(phase.get("checklist", [])) for phase in config.get("phases", [])
    )
    print(f"Total items: {total_items}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="ClickHouse Monthly Release Checklist Executor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Start a new release checklist for June 2026
              python3 tools/release/release_checklist.py --month 2026-06

              # Run only the pre_release phase
              python3 tools/release/release_checklist.py --month 2026-06 --phase pre_release

              # View the status report
              python3 tools/release/release_checklist.py --report --month 2026-06

              # Validate the checklist configuration
              python3 tools/release/release_checklist.py --validate

              # Mark a specific item as complete
              python3 tools/release/release_checklist.py --month 2026-06 --mark-complete verify-ci-green
        """),
    )
    parser.add_argument(
        "--month",
        type=str,
        default=None,
        help="Target release month (YYYY-MM format)",
    )
    parser.add_argument(
        "--phase",
        type=str,
        default=None,
        help="Execute only a specific phase (e.g., pre_release, tag_release)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the checklist configuration",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show the current status report",
    )
    parser.add_argument(
        "--mark-complete",
        type=str,
        default=None,
        help="Mark a specific checklist item as complete",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be checked without executing",
    )
    args = parser.parse_args()

    if args.validate:
        success = validate_config()
        sys.exit(0 if success else 1)

    if args.report:
        if not args.month:
            months = sorted(
                [f.stem for f in STATE_DIR.glob("*.json")],
                reverse=True,
            ) if STATE_DIR.exists() else []
            if not months:
                print("No release checklist state found. Start one with --month YYYY-MM")
                sys.exit(1)
            args.month = months[0]

        state = load_state(args.month)
        if state is None:
            print(f"No state found for month {args.month}")
            sys.exit(1)
        print_report(state)
        sys.exit(0)

    if not args.month:
        parser.error("--month is required (e.g., --month 2026-06)")

    try:
        datetime.datetime.strptime(args.month, "%Y-%m")
    except ValueError:
        parser.error("--month must be in YYYY-MM format")

    if args.mark_complete:
        state = load_state(args.month)
        if state is None:
            print(f"No state found for month {args.month}")
            sys.exit(1)

        found = False
        for phase_data in state.get("phases", []):
            phase = ReleasePhase.from_dict(phase_data)
            for item in phase.items:
                if item.id == args.mark_complete:
                    item.completed = True
                    item.timestamp = datetime.datetime.now().isoformat()
                    found = True
                    print(f"Marked '{item.name}' as complete")
                phase_data["items"] = [item.to_dict() for item in phase.items]
            if found:
                break

        if not found:
            print(f"Checklist item '{args.mark_complete}' not found")
            sys.exit(1)

        save_state(args.month, state)
        sys.exit(0)

    config = load_checklist_config()
    state = load_state(args.month)

    if state is None:
        print(f"Initializing new release checklist for {args.month}")
        state = init_state(args.month, config)
        save_state(args.month, state)

    if args.dry_run:
        print(f"\nDry run for {args.month}:")
        for phase_data in state.get("phases", []):
            phase = ReleasePhase.from_dict(phase_data)
            print(f"\n  Phase: {phase.name}")
            for item in phase.items:
                auto_label = "[AUTO]" if item.automated else "[MANUAL]"
                print(f"    {auto_label} {item.name}")
        sys.exit(0)

    variables = {
        "month": args.month,
        "branch": f"{args.month[:4]}.{int(args.month[5:])}",
        "version": getattr(args, "version", args.month),
        "previous_version": getattr(args, "previous_version", ""),
    }

    execute_checklist(state, variables, args.phase)
    save_state(args.month, state)
    print_report(state)


if __name__ == "__main__":
    main()