"""Pydantic schemas for extraction output and session state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Extraction schema ------------------------------------------------------


class Application(BaseModel):
    name: str
    environment: str
    access_method: str
    notes: str


class ErrorException(BaseModel):
    name: str
    action: str
    parameters: str
    handling: str


class Step(BaseModel):
    number: int
    summary: str
    application: str
    screen: str
    action_detail: str
    data_inputs: list[str]
    data_outputs: list[str]
    decision_logic: str
    exception_paths: list[str]
    success_criterion: str
    group: str
    design_note: str


class ReportRow(BaseModel):
    report_type: str
    update_frequency: str
    details: str
    monitoring_tool: str


class Extracted(BaseModel):
    project_name: str
    business_owner: str
    summary: str
    document_processing: list[str]
    artificial_intelligence: list[str]
    credential_management: str
    tool_selection_rationale: str
    business_criticality: str
    complexity_score: str
    applications: list[Application]
    known_errors: list[ErrorException]
    accepted_failure_threshold: str
    rerun_on_failure: str
    schedule_frequency: str
    bot_utilization_pct: str
    triggers: str
    reports: list[ReportRow]
    steps: list[Step] = Field(default_factory=list)
    applications_diagram_mermaid: str = ""


# --- Session schema ---------------------------------------------------------

InputStyle = Literal["drop_in", "chat"]
Phase = Literal["intake", "narrative", "clarification", "ready_to_generate", "generated"]
TriggerType = Literal["scheduled", "manual", "event", "other"]
Criticality = Literal["low", "medium", "high", "critical"]


class Intake(BaseModel):
    project_name: str | None = None
    business_owner: str | None = None
    trigger_type: TriggerType | None = None
    trigger_detail: str | None = None
    frequency: str | None = None
    applications_rough: list[str] = Field(default_factory=list)
    criticality: Criticality | None = None


class ChatMessage(BaseModel):
    role: Literal["assistant", "user"]
    content: str
    ts: str


class CoverageItem(BaseModel):
    id: str
    category: str
    status: Literal["covered", "partial", "missing"]
    question: str


class Coverage(BaseModel):
    overall_pct: float
    by_category: dict[str, float] = Field(default_factory=dict)
    items: list[CoverageItem] = Field(default_factory=list)


class ClarificationGap(BaseModel):
    """One row in the clarification cursor: the gap to fill, how many times
    we've asked, and (once we move past it) whether the user resolved it."""

    item: CoverageItem
    attempts: int = 0
    final_status: Literal["satisfied", "unresolved"] | None = None


class Session(BaseModel):
    session_id: str
    input_style: InputStyle
    phase: Phase = "intake"
    intake: Intake | None = None
    raw_input: str | None = None
    transcript: list[ChatMessage] = Field(default_factory=list)
    extracted: Extracted | None = None
    coverage: Coverage | None = None
    clarification_cursor: list[ClarificationGap] = Field(default_factory=list)
    clarification_position: int = 0
    generated_files: list[str] = Field(default_factory=list)
