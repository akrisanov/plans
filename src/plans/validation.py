from __future__ import annotations

import re
import sys
from pathlib import Path

from plans.config import (
    PLACEHOLDERS,
    REQUIRED_READY_SECTIONS,
    STATE_STATUS,
)
from plans.models import PlanState
from plans.storage import (
    display_path,
    read_document,
    read_metadata,
)


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


def collect_validation_errors(
    state: PlanState,
    path: Path,
) -> list[str]:
    errors: list[str] = []

    _, body = read_document(path)
    metadata = read_metadata(path)

    if metadata.id != path.stem:
        errors.append(
            f"plan id '{metadata.id}' does not match filename '{path.stem}.md'"
        )

    expected_status = STATE_STATUS[state]

    if metadata.status != expected_status:
        errors.append(
            f"status '{metadata.status}' does not match directory "
            f"state '{state}' (expected '{expected_status}')"
        )

    if is_placeholder(metadata.id):
        errors.append("metadata field 'id' contains a placeholder")

    if is_placeholder(metadata.repository):
        errors.append("metadata field 'repository' contains a placeholder")

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


def ensure_plan_valid(state: PlanState, path: Path) -> None:
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
