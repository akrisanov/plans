from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PlanState = Literal[
    "drafts",
    "next",
    "open",
    "done",
    "discarded",
]

PlanStatus = Literal[
    "draft",
    "next",
    "open",
    "done",
    "discarded",
]


class PlanMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: PlanStatus
    repository: str

    created_at: date
    updated_at: date

    depends_on: list[str] = Field(default_factory=list)
    prs: list[str] = Field(default_factory=list)


class PlanInspection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    state: PlanState
    status: PlanStatus
    repository: str
    created_at: date
    updated_at: date
    depends_on: list[str]
    prs: list[str]
    path: str
