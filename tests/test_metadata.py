from __future__ import annotations

from pathlib import Path

import pytest

from plans.models import PlanMetadata
from plans.storage import read_metadata


def write_plan(
    tmp_path: Path,
    frontmatter: str,
) -> Path:
    path = tmp_path / "test-plan.md"

    path.write_text(
        f"""---
{frontmatter}
---

# Test plan
""",
        encoding="utf-8",
    )

    return path


def test_read_metadata_returns_typed_model(
    tmp_path: Path,
) -> None:
    path = write_plan(
        tmp_path,
        """id: test-plan
status: draft
repository: plans
created_at: 2026-09-13
updated_at: 2026-09-13
depends_on: []
prs: []
""",
    )

    metadata = read_metadata(path)

    assert isinstance(metadata, PlanMetadata)

    assert metadata.id == "test-plan"
    assert metadata.status == "draft"
    assert metadata.repository == "plans"

    assert metadata.created_at.isoformat() == "2026-09-13"
    assert metadata.updated_at.isoformat() == "2026-09-13"

    assert metadata.depends_on == []
    assert metadata.prs == []


def test_read_metadata_rejects_invalid_status(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_plan(
        tmp_path,
        """id: test-plan
status: unknown
repository: plans
created_at: 2026-09-13
updated_at: 2026-09-13
depends_on: []
prs: []
""",
    )

    with pytest.raises(SystemExit) as exc_info:
        read_metadata(path)

    assert exc_info.value.code == 1

    stderr = capsys.readouterr().err

    assert "invalid plan metadata" in stderr
    assert "status" in stderr


def test_read_metadata_rejects_invalid_date(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_plan(
        tmp_path,
        """id: test-plan
status: draft
repository: plans
created_at: not-a-date
updated_at: 2026-09-13
depends_on: []
prs: []
""",
    )

    with pytest.raises(SystemExit) as exc_info:
        read_metadata(path)

    assert exc_info.value.code == 1

    stderr = capsys.readouterr().err

    assert "invalid plan metadata" in stderr
    assert "created_at" in stderr


def test_read_metadata_rejects_invalid_depends_on_type(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_plan(
        tmp_path,
        """id: test-plan
status: draft
repository: plans
created_at: 2026-09-13
updated_at: 2026-09-13
depends_on: test-plan
prs: []
""",
    )

    with pytest.raises(SystemExit) as exc_info:
        read_metadata(path)

    assert exc_info.value.code == 1

    stderr = capsys.readouterr().err

    assert "invalid plan metadata" in stderr
    assert "depends_on" in stderr


def test_read_metadata_rejects_extra_field(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_plan(
        tmp_path,
        """id: test-plan
status: draft
repository: plans
created_at: 2026-09-13
updated_at: 2026-09-13
depends_on: []
prs: []
unexpected: value
""",
    )

    with pytest.raises(SystemExit) as exc_info:
        read_metadata(path)

    assert exc_info.value.code == 1

    stderr = capsys.readouterr().err

    assert "invalid plan metadata" in stderr
    assert "unexpected" in stderr


def test_read_metadata_rejects_missing_required_field(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_plan(
        tmp_path,
        """id: test-plan
status: draft
created_at: 2026-09-13
updated_at: 2026-09-13
depends_on: []
prs: []
""",
    )

    with pytest.raises(SystemExit) as exc_info:
        read_metadata(path)

    assert exc_info.value.code == 1

    stderr = capsys.readouterr().err

    assert "invalid plan metadata" in stderr
    assert "repository" in stderr
