"""Pydantic schemas for extraction output and session state.

Mirrors spec.md → 'Extraction schema' and 'Session schema'.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Extraction schema ------------------------------------------------------


class Application(BaseModel):
    name: str
    version: str | None = None
    language: str | None = None
    environment: str | None = None
    access_method: str | None = None
    notes: str | None = None


class ErrorException(BaseModel):
    name: str
    action: str | None = None
    parameters: str | None = None
    handling: str | None = None


class Step(BaseModel):
    number: int
    summary: str
    application: str | None = None
    screen: str | None = None
    action_detail: str | None = None
    data_inputs: list[str] = Field(default_factory=list)
    data_outputs: list[str] = Field(default_factory=list)
    decision_logic: str | None = None
    exception_paths: list[str] = Field(default_factory=list)
    success_criterion: str | None = None


class ReportRow(BaseModel):
    report_type: str
    update_frequency: str | None = None
    details: str | None = None
    monitoring_tool: str | None = None


class Extracted(BaseModel):
    project_name: str
    business_owner: str | None = None
    summary: str
    automation_tools: list[str] = Field(default_factory=list)
    btp_services: list[str] = Field(default_factory=list)
    document_processing: list[str] = Field(default_factory=list)
    new_sdks_objects: list[str] = Field(default_factory=list)
    artificial_intelligence: list[str] = Field(default_factory=list)
    credential_management: str | None = None
    tool_selection_rationale: str | None = None
    business_criticality: str | None = None
    complexity_score: str | None = None
    applications: list[Application] = Field(default_factory=list)
    known_errors: list[ErrorException] = Field(default_factory=list)
    accepted_failure_threshold: str | None = None
    rerun_on_failure: str | None = None
    schedule_frequency: str | None = None
    bot_utilization_pct: float | None = None
    triggers: str | None = None
    reports: list[ReportRow] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    applications_diagram_mermaid: str | None = None


# --- Session schema ---------------------------------------------------------

Mode = Literal["technology_fit", "sdd_builder"]
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
    question: str | None = None


class Coverage(BaseModel):
    overall_pct: float
    by_category: dict[str, float] = Field(default_factory=dict)
    items: list[CoverageItem] = Field(default_factory=list)


class Session(BaseModel):
    session_id: str
    mode: Mode
    input_style: InputStyle
    phase: Phase = "intake"
    intake: Intake | None = None
    raw_input: str | None = None
    transcript: list[ChatMessage] = Field(default_factory=list)
    extracted: Extracted | None = None
    coverage: Coverage | None = None
    generated_files: list[str] = Field(default_factory=list)
