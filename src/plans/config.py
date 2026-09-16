from __future__ import annotations

import os
import re
from importlib.resources import files
from pathlib import Path

from plans.models import PlanState, PlanStatus

PLANS_HOME = Path(
    os.environ.get(
        "PLANS_HOME",
        Path.home() / ".local" / "share" / "plans",
    )
).expanduser()

PLANS_DIR = PLANS_HOME / "plans"
PLAN_TEMPLATE = files("plans").joinpath("templates/plan.md")

PLAN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

STATES: tuple[PlanState, ...] = (
    "drafts",
    "next",
    "open",
    "done",
    "discarded",
)

STATE_STATUS: dict[PlanState, PlanStatus] = {
    "drafts": "draft",
    "next": "next",
    "open": "open",
    "done": "done",
    "discarded": "discarded",
}

TRANSITIONS: dict[PlanState, set[PlanState]] = {
    "drafts": {"next", "discarded"},
    "next": {"open", "discarded"},
    "open": {"done", "discarded"},
    "done": set(),
    "discarded": set(),
}

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
