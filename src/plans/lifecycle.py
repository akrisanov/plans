from __future__ import annotations

import shutil
from datetime import UTC, datetime

from plans.config import PLANS_DIR, STATE_STATUS, TRANSITIONS
from plans.storage import (
    display_path,
    fail,
    find_plan,
    read_metadata,
    update_metadata,
)
from plans.validation import ensure_plan_complete, ensure_plan_valid


def transition_plan(
    plan_id: str,
    target_state: str,
) -> None:
    source_state, source_path = find_plan(plan_id)

    if source_state == "open" and target_state == "done":
        fail("direct transition from open to done is not allowed; use 'plan complete'")

    if target_state not in TRANSITIONS[source_state]:
        fail(f"invalid transition: {source_state} -> {target_state}")

    if source_state == "drafts" and target_state == "next":
        ensure_plan_valid(source_state, source_path)

    target_dir = PLANS_DIR / target_state
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / source_path.name

    if target_path.exists():
        fail(f"target already exists: {display_path(target_path)}")

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

    print(f"{plan_id}: {source_state} -> {target_state}")
    print(display_path(target_path))


def ready_plan(plan_id: str) -> None:
    state, _ = find_plan(plan_id)

    if state != "drafts":
        fail(f"plan is not a draft: {plan_id} (current state: {state})")

    transition_plan(plan_id, "next")


def complete_plan(plan_id: str) -> None:
    state, path = find_plan(plan_id)

    if state != "open":
        fail(f"plan is not open: {plan_id} (current state: {state})")

    ensure_plan_complete(path)

    target_dir = PLANS_DIR / "done"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / path.name
    if target_path.exists():
        fail(f"target already exists: {display_path(target_path)}")

    previous_updated_at = read_metadata(path).updated_at.isoformat()
    update_metadata(
        path,
        status=STATE_STATUS["done"],
        updated_at=datetime.now(UTC).date().isoformat(),
    )
    try:
        shutil.move(path, target_path)
    except Exception:
        update_metadata(
            path,
            status=STATE_STATUS["open"],
            updated_at=previous_updated_at,
        )
        raise

    print(f"{plan_id}: open -> done")
    print(display_path(target_path))
