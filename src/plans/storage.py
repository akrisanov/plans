from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NoReturn

from plans.config import PLANS_DIR, PLANS_HOME, STATE_STATUS, STATES


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
