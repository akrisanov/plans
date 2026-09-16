from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from plans.config import (
    PLAN_ID_PATTERN,
    PLAN_TEMPLATE,
    PLANS_DIR,
    STATES,
)
from plans.lifecycle import ready_plan, transition_plan
from plans.storage import (
    display_path,
    fail,
    find_plan,
    find_plan_matches,
    inspect_plan,
    read_metadata,
    validate_plan_state,
)
from plans.validation import ensure_plan_valid


def validate_plan_id(plan_id: str) -> None:
    if not PLAN_ID_PATTERN.fullmatch(plan_id):
        fail(
            "invalid plan id: "
            f"'{plan_id}' "
            "(expected lowercase kebab-case, "
            "e.g. 'add-plan-cli')"
        )


def command_add(args: argparse.Namespace) -> None:
    validate_plan_id(args.id)

    if find_plan_matches(args.id):
        fail(f"plan already exists: {args.id}")

    repository = args.repository.strip()

    if not repository:
        fail("repository must not be empty")

    if not PLAN_TEMPLATE.is_file():
        fail(f"plan template not found: {PLAN_TEMPLATE}")

    drafts_dir = PLANS_DIR / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    target_path = drafts_dir / f"{args.id}.md"

    if target_path.exists():
        fail(f"target already exists: {display_path(target_path)}")

    today = datetime.now(UTC).date().isoformat()
    content = PLAN_TEMPLATE.read_text(encoding="utf-8")

    replacements = {
        "id: TODO": f"id: {args.id}",
        "repository: TODO": f"repository: {repository}",
        "created_at: YYYY-MM-DD": f"created_at: {today}",
        "updated_at: YYYY-MM-DD": f"updated_at: {today}",
    }

    for source, replacement in replacements.items():
        if content.count(source) != 1:
            fail(f"unexpected plan template format: expected exactly one '{source}'")

        content = content.replace(source, replacement, 1)

    target_path.write_text(content, encoding="utf-8")

    print(f"{args.id}: created")
    print(display_path(target_path))


def command_list(_: argparse.Namespace) -> None:
    found = False

    for state in STATES:
        state_dir = PLANS_DIR / state

        if not state_dir.is_dir():
            continue

        plans: list[tuple[str, Path]] = []

        for path in sorted(state_dir.glob("*.md")):
            metadata = read_metadata(path)

            validate_plan_state(state, path)
            plans.append((metadata.id, path))

        if not plans:
            continue

        found = True
        print(state.upper())

        for plan_id, path in plans:
            print(f"  {plan_id:<40} {path.name}")

        print()

    if not found:
        print("No plans found.")


def command_show(args: argparse.Namespace) -> None:
    state, path = find_plan(args.id)

    print(f"state: {state}")
    print(f"path:  {display_path(path)}")
    print()
    print(path.read_text(encoding="utf-8"), end="")


def command_inspect(args: argparse.Namespace) -> None:
    inspection = inspect_plan(args.id)
    print(json.dumps(inspection.model_dump(mode="json")))


def command_validate(args: argparse.Namespace) -> None:
    state, path = find_plan(args.id)
    ensure_plan_valid(state, path)

    print(f"{args.id}: valid")


def command_ready(args: argparse.Namespace) -> None:
    ready_plan(args.id)


def command_transition(args: argparse.Namespace) -> None:
    transition_plan(args.id, args.state)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plan",
        description="Manage plans and their lifecycle.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    add_parser = subparsers.add_parser(
        "add",
        help="Create a new draft plan from the plan template.",
    )
    add_parser.add_argument("id")
    add_parser.add_argument(
        "--repository",
        required=True,
        help="Logical repository name for the plan.",
    )
    add_parser.set_defaults(func=command_add)

    list_parser = subparsers.add_parser(
        "list",
        help="List all plans grouped by state.",
    )
    list_parser.set_defaults(func=command_list)

    show_parser = subparsers.add_parser(
        "show",
        help="Show a plan by ID.",
    )
    show_parser.add_argument("id")
    show_parser.set_defaults(func=command_show)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a plan in a machine-readable format.",
    )
    inspect_parser.add_argument("id")
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        required=True,
        help="Return the inspection result as JSON.",
    )
    inspect_parser.set_defaults(func=command_inspect)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate that a plan is ready for implementation.",
    )
    validate_parser.add_argument("id")
    validate_parser.set_defaults(func=command_validate)

    ready_parser = subparsers.add_parser(
        "ready",
        help="Validate a draft plan and move it to the next state.",
    )
    ready_parser.add_argument("id")
    ready_parser.set_defaults(func=command_ready)

    transition_parser = subparsers.add_parser(
        "transition",
        help="Move a plan to another lifecycle state.",
    )
    transition_parser.add_argument("id")
    transition_parser.add_argument(
        "state",
        choices=STATES,
    )
    transition_parser.set_defaults(func=command_transition)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
