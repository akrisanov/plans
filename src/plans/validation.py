from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from plans.config import (
    PLACEHOLDERS,
    REQUIRED_METADATA,
    REQUIRED_READY_SECTIONS,
    STATE_STATUS,
)
from plans.storage import display_path, read_document


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
