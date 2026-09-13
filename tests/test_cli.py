from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def run_plan(
    plans_home: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PLANS_HOME"] = str(plans_home)

    return subprocess.run(
        [sys.executable, "-m", "plans.cli", *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def make_ready(plan_path: Path) -> None:
    content = plan_path.read_text(encoding="utf-8")

    replacements = {
        "## Problem\n\nTODO": "## Problem\n\nNeed to verify the ready command.",
        "## Goal\n\nTODO": "## Goal\n\nMove a valid draft to next.",
        "## Decisions\n\nTODO": (
            "## Decisions\n\nUse the existing lifecycle transition logic."
        ),
        "## Implementation\n\nTODO": (
            "## Implementation\n\nRun the ready command against the draft."
        ),
        "## Verification\n\nTODO": (
            "## Verification\n\nConfirm the plan moves to the next state."
        ),
        "## Done when\n\n- [ ] TODO": (
            "## Done when\n\n- [ ] Plan is moved to the next state."
        ),
    }

    for source, replacement in replacements.items():
        assert source in content
        content = content.replace(source, replacement, 1)

    plan_path.write_text(content, encoding="utf-8")


def create_ready_plan(
    plans_home: Path,
    plan_id: str = "test-plan",
) -> Path:
    result = run_plan(
        plans_home,
        "add",
        plan_id,
        "--repository",
        "plans",
    )

    assert result.returncode == 0

    plan_path = plans_home / "plans" / "drafts" / f"{plan_id}.md"
    make_ready(plan_path)

    return plan_path


def test_add_creates_draft(tmp_path: Path) -> None:
    result = run_plan(
        tmp_path,
        "add",
        "test-plan",
        "--repository",
        "plans",
    )

    assert result.returncode == 0
    assert "test-plan: created" in result.stdout

    plan_path = tmp_path / "plans" / "drafts" / "test-plan.md"

    assert plan_path.is_file()

    content = plan_path.read_text(encoding="utf-8")

    assert "id: test-plan" in content
    assert "status: draft" in content
    assert "repository: plans" in content


def test_add_rejects_invalid_id(tmp_path: Path) -> None:
    result = run_plan(
        tmp_path,
        "add",
        "Test_Plan",
        "--repository",
        "plans",
    )

    assert result.returncode == 1
    assert "invalid plan id" in result.stderr


def test_add_rejects_duplicate_id(tmp_path: Path) -> None:
    first_result = run_plan(
        tmp_path,
        "add",
        "test-plan",
        "--repository",
        "plans",
    )

    assert first_result.returncode == 0

    second_result = run_plan(
        tmp_path,
        "add",
        "test-plan",
        "--repository",
        "plans",
    )

    assert second_result.returncode == 1
    assert "plan already exists: test-plan" in second_result.stderr


def test_add_rejects_empty_repository(tmp_path: Path) -> None:
    result = run_plan(
        tmp_path,
        "add",
        "test-plan",
        "--repository",
        "",
    )

    assert result.returncode == 1
    assert "repository must not be empty" in result.stderr


def test_fresh_draft_fails_validation(tmp_path: Path) -> None:
    add_result = run_plan(
        tmp_path,
        "add",
        "test-plan",
        "--repository",
        "plans",
    )

    assert add_result.returncode == 0

    result = run_plan(tmp_path, "validate", "test-plan")

    assert result.returncode == 1
    assert "plan validation failed" in result.stderr
    assert "Problem" in result.stderr
    assert "Done when" in result.stderr


def test_ready_moves_valid_draft_to_next(tmp_path: Path) -> None:
    draft_path = create_ready_plan(tmp_path)

    result = run_plan(tmp_path, "ready", "test-plan")

    assert result.returncode == 0
    assert "test-plan: drafts -> next" in result.stdout

    next_path = tmp_path / "plans" / "next" / "test-plan.md"

    assert not draft_path.exists()
    assert next_path.is_file()

    content = next_path.read_text(encoding="utf-8")

    assert "status: next" in content


def test_ready_rejects_non_draft(tmp_path: Path) -> None:
    create_ready_plan(tmp_path)

    first_result = run_plan(tmp_path, "ready", "test-plan")

    assert first_result.returncode == 0

    second_result = run_plan(tmp_path, "ready", "test-plan")

    assert second_result.returncode == 1
    assert (
        "plan is not a draft: test-plan (current state: next)" in second_result.stderr
    )


def test_transition_next_to_open(tmp_path: Path) -> None:
    create_ready_plan(tmp_path)

    ready_result = run_plan(tmp_path, "ready", "test-plan")

    assert ready_result.returncode == 0

    result = run_plan(
        tmp_path,
        "transition",
        "test-plan",
        "open",
    )

    assert result.returncode == 0
    assert "test-plan: next -> open" in result.stdout

    open_path = tmp_path / "plans" / "open" / "test-plan.md"

    assert open_path.is_file()
    assert "status: open" in open_path.read_text(encoding="utf-8")


def test_transition_open_to_done(tmp_path: Path) -> None:
    create_ready_plan(tmp_path)

    ready_result = run_plan(tmp_path, "ready", "test-plan")
    assert ready_result.returncode == 0

    open_result = run_plan(
        tmp_path,
        "transition",
        "test-plan",
        "open",
    )
    assert open_result.returncode == 0

    result = run_plan(
        tmp_path,
        "transition",
        "test-plan",
        "done",
    )

    assert result.returncode == 0
    assert "test-plan: open -> done" in result.stdout

    done_path = tmp_path / "plans" / "done" / "test-plan.md"

    assert done_path.is_file()
    assert "status: done" in done_path.read_text(encoding="utf-8")


def test_transition_rejects_invalid_transition(tmp_path: Path) -> None:
    add_result = run_plan(
        tmp_path,
        "add",
        "test-plan",
        "--repository",
        "plans",
    )

    assert add_result.returncode == 0

    result = run_plan(
        tmp_path,
        "transition",
        "test-plan",
        "done",
    )

    assert result.returncode == 1
    assert "invalid transition: drafts -> done" in result.stderr


def test_detects_state_status_mismatch(tmp_path: Path) -> None:
    add_result = run_plan(
        tmp_path,
        "add",
        "test-plan",
        "--repository",
        "plans",
    )

    assert add_result.returncode == 0

    plan_path = tmp_path / "plans" / "drafts" / "test-plan.md"
    content = plan_path.read_text(encoding="utf-8")
    content = content.replace("status: draft", "status: next", 1)
    plan_path.write_text(content, encoding="utf-8")

    result = run_plan(tmp_path, "show", "test-plan")

    assert result.returncode == 1
    assert "inconsistent plan state" in result.stderr
    assert "directory 'drafts' expects status 'draft'" in result.stderr


def test_detects_duplicate_id_across_states(tmp_path: Path) -> None:
    add_result = run_plan(
        tmp_path,
        "add",
        "test-plan",
        "--repository",
        "plans",
    )

    assert add_result.returncode == 0

    draft_path = tmp_path / "plans" / "drafts" / "test-plan.md"

    next_dir = tmp_path / "plans" / "next"
    next_dir.mkdir(parents=True)

    duplicate_path = next_dir / "duplicate.md"

    content = draft_path.read_text(encoding="utf-8")
    content = content.replace("status: draft", "status: next", 1)
    duplicate_path.write_text(content, encoding="utf-8")

    result = run_plan(tmp_path, "show", "test-plan")

    assert result.returncode == 1
    assert "duplicate plan id 'test-plan'" in result.stderr
