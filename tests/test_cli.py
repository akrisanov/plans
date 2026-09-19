from __future__ import annotations

import json
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


def test_inspect_returns_plan_as_json(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plans" / "open"
    plan_dir.mkdir(parents=True)
    plan_path = plan_dir / "test-plan.md"
    plan_path.write_text(
        """---
id: test-plan
status: open
repository: plans
created_at: 2026-09-13
updated_at: 2026-09-16
depends_on:
  - first-plan
prs:
  - https://example.com/pull/1
---

# Test plan
""",
        encoding="utf-8",
    )

    result = run_plan(tmp_path, "inspect", "test-plan", "--json")

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "id": "test-plan",
        "state": "open",
        "status": "open",
        "repository": "plans",
        "created_at": "2026-09-13",
        "updated_at": "2026-09-16",
        "depends_on": ["first-plan"],
        "prs": ["https://example.com/pull/1"],
        "path": "plans/open/test-plan.md",
    }
    assert str(tmp_path) not in result.stdout


def test_inspect_rejects_unknown_plan(tmp_path: Path) -> None:
    result = run_plan(tmp_path, "inspect", "unknown-plan", "--json")

    assert result.returncode != 0
    assert "plan not found: unknown-plan" in result.stderr


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


def open_plan(tmp_path: Path, plan_id: str = "test-plan") -> Path:
    create_ready_plan(tmp_path, plan_id)
    assert run_plan(tmp_path, "ready", plan_id).returncode == 0
    assert run_plan(tmp_path, "transition", plan_id, "open").returncode == 0
    return tmp_path / "plans" / "open" / f"{plan_id}.md"


def make_complete(path: Path, deviations: str = "None") -> None:
    content = path.read_text(encoding="utf-8")
    content = content.replace("- [ ] Plan is moved", "- [x] Plan is moved", 1)
    content = content.replace("- Commit:", "- Commit: abc123", 1)
    content = content.replace(
        "### Verification\n\nTODO", "### Verification\n\nAll tests passed.", 1
    )
    content = content.replace(
        "### Deviations\n\nTODO", f"### Deviations\n\n{deviations}", 1
    )
    path.write_text(content, encoding="utf-8")


def test_complete_open_plan(tmp_path: Path) -> None:
    source = open_plan(tmp_path)
    make_complete(source)

    result = run_plan(tmp_path, "complete", "test-plan")

    assert result.returncode == 0
    assert "test-plan: open -> done" in result.stdout
    assert not source.exists()
    done = tmp_path / "plans" / "done" / "test-plan.md"
    assert done.is_file()
    assert "status: done" in done.read_text(encoding="utf-8")


def test_transition_open_to_done_is_rejected(tmp_path: Path) -> None:
    source = open_plan(tmp_path)
    original = source.read_text(encoding="utf-8")

    result = run_plan(tmp_path, "transition", "test-plan", "done")

    assert result.returncode == 1
    assert "use 'plan complete'" in result.stderr
    assert source.read_text(encoding="utf-8") == original


def test_complete_rejects_plan_outside_open(tmp_path: Path) -> None:
    create_ready_plan(tmp_path)
    result = run_plan(tmp_path, "complete", "test-plan")
    assert result.returncode == 1
    assert "plan is not open" in result.stderr


def test_complete_rejects_state_status_disagreement(tmp_path: Path) -> None:
    source = open_plan(tmp_path)
    source.write_text(
        source.read_text(encoding="utf-8").replace("status: open", "status: next"),
        encoding="utf-8",
    )
    result = run_plan(tmp_path, "complete", "test-plan")
    assert result.returncode == 1
    assert "inconsistent plan state" in result.stderr


def test_complete_rejections_leave_plan_unchanged(tmp_path: Path) -> None:
    cases = {
        "unchecked": lambda text: text,
        "todo": lambda text: text.replace(
            "### Deviations\n\nTODO", "### Deviations\n\nNone"
        ).replace("- Commit:", "- Commit: abc123"),
        "commit": lambda text: text.replace(
            "### Verification\n\nTODO", "### Verification\n\nPassed"
        ).replace("### Deviations\n\nTODO", "### Deviations\n\nNone"),
        "verification": lambda text: text.replace(
            "- Commit:", "- Commit: abc123"
        ).replace("### Deviations\n\nTODO", "### Deviations\n\nNone"),
        "deviations": lambda text: text.replace(
            "- Commit:", "- Commit: abc123"
        ).replace("### Verification\n\nTODO", "### Verification\n\nPassed"),
    }
    expected = {
        "unchecked": "unchecked items",
        "todo": "unresolved TODO",
        "commit": "non-empty Commit",
        "verification": "Verification must contain",
        "deviations": "Deviations must contain",
    }
    for name, mutate in cases.items():
        plan_id = f"case-{name}"
        path = open_plan(tmp_path, plan_id)
        text = mutate(path.read_text(encoding="utf-8"))
        if name != "unchecked":
            text = text.replace("- [ ] Plan is moved", "- [x] Plan is moved")
        path.write_text(text, encoding="utf-8")
        before = path.read_bytes()
        result = run_plan(tmp_path, "complete", plan_id)
        assert result.returncode == 1
        assert expected[name] in result.stderr
        assert path.read_bytes() == before


def test_complete_rejects_missing_done_when_section(tmp_path: Path) -> None:
    source = open_plan(tmp_path)
    make_complete(source)
    content = source.read_text(encoding="utf-8")
    start = content.index("## Done when\n")
    end = content.index("## Results\n", start)
    source.write_text(content[:start] + content[end:], encoding="utf-8")

    result = run_plan(tmp_path, "complete", "test-plan")

    assert result.returncode == 1
    assert "missing required section: Done when" in result.stderr
    assert source.is_file()


def test_complete_rejects_done_when_without_checkboxes(tmp_path: Path) -> None:
    source = open_plan(tmp_path)
    make_complete(source)
    content = source.read_text(encoding="utf-8").replace(
        "## Done when\n\n- [x] Plan is moved to the next state.",
        "## Done when\n\nCompletion criterion recorded as prose.",
        1,
    )
    source.write_text(content, encoding="utf-8")

    result = run_plan(tmp_path, "complete", "test-plan")

    assert result.returncode == 1
    assert "must contain at least one meaningful checklist item" in result.stderr
    assert source.is_file()


def test_complete_accepts_explicit_none_deviations(tmp_path: Path) -> None:
    source = open_plan(tmp_path)
    make_complete(source, deviations="None")
    assert run_plan(tmp_path, "complete", "test-plan").returncode == 0


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
