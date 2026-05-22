from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class SourceKind(str, Enum):
    file = "file"
    url = "url"
    text = "text"


class TaskCreateResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str


class ToolCall(BaseModel):
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    output_preview: str | None = None
    status: Literal["started", "succeeded", "failed"]
    error: str | None = None
    started_at: datetime
    ended_at: datetime | None = None


class AgentStep(BaseModel):
    id: str
    action: str
    tool: str
    purpose: str
    status: Literal["pending", "running", "succeeded", "failed"] = "pending"


class StructuredResult(BaseModel):
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    quality: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    raw_text_preview: str | None = None


class TaskRecord(BaseModel):
    task_id: str
    status: TaskStatus
    goal: str
    source_kind: SourceKind
    source_name: str
    created_at: datetime
    updated_at: datetime
    plan: list[AgentStep] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    result: StructuredResult | None = None
    error: str | None = None
