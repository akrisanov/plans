#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import UTC, date, datetime
from importlib.resources import files
from pathlib import Path
from typing import NoReturn

PLANS_HOME = Path(
    os.environ.get(
        "PLANS_HOME",
        Path.home() / ".local" / "share" / "plans",
    )
).expanduser()

PLANS_DIR = PLANS_HOME / "plans"
PLAN_TEMPLATE = files("plans").joinpath("templates/plan.md")
PLAN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

STATES = ("drafts", "next", "open", "done", "discarded")

STATE_STATUS = {
    "drafts": "draft",
    "next": "next",
    "open": "open",
    "done": "done",
    "discarded": "discarded",
}

TRANSITIONS = {
    "drafts": {"next", "discarded"},
    "next": {"open", "discarded"},
    "open": {"done", "discarded"},
    "done": set(),
    "discarded": set(),
}

REQUIRED_METADATA = (
    "id",
    "status",
    "repository",
    "created_at",
    "updated_at",
    "depends_on",
    "prs",
)

REQUIRED_READY_SECTIONS = (
    "Problem",
    "Goal",
    "Decisions",
    "Implementation",
    "Verification",
    "Done when",
)

PLACEHOLDERS = {
    "",
    "...",
    "tbd",
    "todo",
    "to do",
    "placeholder",
}


def fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PLANS_HOME))
    except ValueError:
        return str(path)


def read_document(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")

    if not text.startswith("---\n"):
        fail(f"missing YAML frontmatter: {display_path(path)}")

    end = text.find("\n---\n", 4)

    if end == -1:
        fail(f"invalid YAML frontmatter: {display_path(path)}")

    frontmatter = text[4:end]
    body = text[end + len("\n---\n") :]

    return frontmatter, body


def read_metadata_value(path: Path, key: str) -> str | None:
    frontmatter, _ = read_document(path)

    match = re.search(
        rf"^{re.escape(key)}:\s*(.*?)\s*$",
        frontmatter,
        re.MULTILINE,
    )

    if not match:
        return None

    return match.group(1).strip().strip("\"'")


def update_metadata(path: Path, **values: str) -> None:
    frontmatter, body = read_document(path)

    for key, value in values.items():
        pattern = rf"^{re.escape(key)}:\s*.*$"

        if not re.search(pattern, frontmatter, re.MULTILINE):
            fail(f"missing metadata field '{key}': {display_path(path)}")

        frontmatter = re.sub(
            pattern,
            f"{key}: {value}",
            frontmatter,
            flags=re.MULTILINE,
        )

    path.write_text(
        f"---\n{frontmatter}\n---\n{body}",
        encoding="utf-8",
    )


def validate_plan_state(state: str, path: Path) -> None:
    actual_status = read_metadata_value(path, "status")

    if actual_status is None:
        fail(f"missing metadata field 'status': {display_path(path)}")

    expected_status = STATE_STATUS[state]

    if actual_status != expected_status:
        fail(
            f"inconsistent plan state for {display_path(path)}: "
            f"directory '{state}' expects status '{expected_status}', "
            f"got '{actual_status}'"
        )


def validate_plan_id(plan_id: str) -> None:
    if not PLAN_ID_PATTERN.fullmatch(plan_id):
        fail(
            "invalid plan id: "
            f"'{plan_id}' (expected lowercase kebab-case, e.g. 'add-plan-cli')"
        )


def find_plan_matches(plan_id: str) -> list[tuple[str, Path]]:
    matches: list[tuple[str, Path]] = []

    for state in STATES:
        state_dir = PLANS_DIR / state

        if not state_dir.is_dir():
            continue

        for path in state_dir.glob("*.md"):
            if path.stem == plan_id or read_metadata_value(path, "id") == plan_id:
                matches.append((state, path))

    return matches


def find_plan(plan_id: str) -> tuple[str, Path]:
    matches = find_plan_matches(plan_id)

    if not matches:
        fail(f"plan not found: {plan_id}")

    if len(matches) > 1:
        locations = ", ".join(display_path(path) for _, path in matches)

        fail(f"duplicate plan id '{plan_id}': {locations}")

    state, path = matches[0]
    validate_plan_state(state, path)

    return state, path


def extract_section(body: str, heading: str) -> str | None:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$"
        rf"(.*?)"
        rf"(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    match = pattern.search(body)

    if not match:
        return None

    return match.group(1).strip()


def is_placeholder(content: str) -> bool:
    normalized = content.strip().lower()

    if normalized in PLACEHOLDERS:
        return True

    return any(
        line.strip().lower() in PLACEHOLDERS - {""}
        for line in content.splitlines()
        if line.strip()
    )


def has_meaningful_checklist_item(content: str) -> bool:
    pattern = re.compile(
        r"^\s*-\s*\[(?: |x|X)\]\s+(.+?)\s*$",
        re.MULTILINE,
    )

    for match in pattern.finditer(content):
        item = match.group(1).strip()

        if not is_placeholder(item):
            return True

    return False


def is_valid_date(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False

    try:
        date.fromisoformat(value)
    except ValueError:
        return False

    return True


def collect_validation_errors(
    state: str,
    path: Path,
) -> list[str]:
    errors: list[str] = []

    frontmatter, body = read_document(path)

    metadata: dict[str, str | None] = {}

    for key in REQUIRED_METADATA:
        match = re.search(
            rf"^{re.escape(key)}:\s*(.*?)\s*$",
            frontmatter,
            re.MULTILINE,
        )

        if match:
            metadata[key] = match.group(1).strip().strip("\"'")
        else:
            metadata[key] = None

    for key in REQUIRED_METADATA:
        value = metadata[key]

        if value is None:
            errors.append(f"missing metadata field: {key}")
            continue

        if key not in {"depends_on", "prs"} and not value:
            errors.append(f"metadata field is empty: {key}")

    plan_id = metadata["id"]

    if plan_id and plan_id != path.stem:
        errors.append(f"plan id '{plan_id}' does not match filename '{path.stem}.md'")

    status = metadata["status"]
    expected_status = STATE_STATUS[state]

    if status and status != expected_status:
        errors.append(
            f"status '{status}' does not match directory "
            f"state '{state}' (expected '{expected_status}')"
        )

    for key in ("created_at", "updated_at"):
        value = metadata[key]

        if value and not is_valid_date(value):
            errors.append(f"metadata field '{key}' must use a valid YYYY-MM-DD date")

    for key in ("id", "repository"):
        value = metadata[key]

        if value and is_placeholder(value):
            errors.append(f"metadata field '{key}' contains a placeholder")

    for heading in REQUIRED_READY_SECTIONS:
        content = extract_section(body, heading)

        if content is None:
            errors.append(f"missing required section: {heading}")
            continue

        if is_placeholder(content):
            errors.append(f"required section contains no meaningful content: {heading}")

    done_when = extract_section(body, "Done when")

    if done_when is not None and not has_meaningful_checklist_item(done_when):
        errors.append(
            "section 'Done when' must contain at least one meaningful checklist item"
        )

    return errors


def ensure_plan_valid(state: str, path: Path) -> None:
    errors = collect_validation_errors(state, path)

    if not errors:
        return

    print(
        f"error: plan validation failed: {display_path(path)}",
        file=sys.stderr,
    )

    for error in errors:
        print(f"  - {error}", file=sys.stderr)

    raise SystemExit(1)


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
            plan_id = read_metadata_value(path, "id")

            if plan_id is None:
                fail(f"missing metadata field 'id': {display_path(path)}")

            validate_plan_state(state, path)
            plans.append((plan_id, path))

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


def command_validate(args: argparse.Namespace) -> None:
    state, path = find_plan(args.id)
    ensure_plan_valid(state, path)

    print(f"{args.id}: valid")


def command_ready(args: argparse.Namespace) -> None:
    state, _ = find_plan(args.id)

    if state != "drafts":
        fail(f"plan is not a draft: {args.id} (current state: {state})")

    args.state = "next"
    command_transition(args)


def command_transition(args: argparse.Namespace) -> None:
    source_state, source_path = find_plan(args.id)
    target_state = args.state

    if target_state not in TRANSITIONS[source_state]:
        fail(f"invalid transition: {source_state} -> {target_state}")

    if source_state == "drafts" and target_state == "next":
        ensure_plan_valid(source_state, source_path)

    target_dir = PLANS_DIR / target_state
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / source_path.name

    if target_path.exists():
        fail(f"target already exists: {display_path(target_path)}")

    for key in ("status", "updated_at"):
        if read_metadata_value(source_path, key) is None:
            fail(f"missing metadata field '{key}': {display_path(source_path)}")

    update_metadata(
        source_path,
        status=STATE_STATUS[target_state],
        updated_at=datetime.now(UTC).date().isoformat(),
    )

    try:
        shutil.move(source_path, target_path)
    except Exception:
        update_metadata(
            source_path,
            status=STATE_STATUS[source_state],
        )
        raise

    print(f"{args.id}: {source_state} -> {target_state}")
    print(display_path(target_path))


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
