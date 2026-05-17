"""Pydantic schemas for extraction output and session state.

Mirrors spec.md → 'Extraction schema' and 'Session schema'.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- Extraction schema ------------------------------------------------------


class Application(BaseModel):
    name: str
    version: Optional[str] = None
    language: Optional[str] = None
    environment: Optional[str] = None
    access_method: Optional[str] = None
    notes: Optional[str] = None


class ErrorException(BaseModel):
    name: str
    action: Optional[str] = None
    parameters: Optional[str] = None
    handling: Optional[str] = None


class Step(BaseModel):
    number: int
    summary: str
    application: Optional[str] = None
    screen: Optional[str] = None
    action_detail: Optional[str] = None
    data_inputs: list[str] = Field(default_factory=list)
    data_outputs: list[str] = Field(default_factory=list)
    decision_logic: Optional[str] = None
    exception_paths: list[str] = Field(default_factory=list)
    success_criterion: Optional[str] = None


class ReportRow(BaseModel):
    report_type: str
    update_frequency: Optional[str] = None
    details: Optional[str] = None
    monitoring_tool: Optional[str] = None


class Extracted(BaseModel):
    project_name: str
    business_owner: Optional[str] = None
    summary: str
    automation_tools: list[str] = Field(default_factory=list)
    btp_services: list[str] = Field(default_factory=list)
    document_processing: list[str] = Field(default_factory=list)
    new_sdks_objects: list[str] = Field(default_factory=list)
    artificial_intelligence: list[str] = Field(default_factory=list)
    credential_management: Optional[str] = None
    tool_selection_rationale: Optional[str] = None
    business_criticality: Optional[str] = None
    complexity_score: Optional[str] = None
    applications: list[Application] = Field(default_factory=list)
    known_errors: list[ErrorException] = Field(default_factory=list)
    accepted_failure_threshold: Optional[str] = None
    rerun_on_failure: Optional[str] = None
    schedule_frequency: Optional[str] = None
    bot_utilization_pct: Optional[float] = None
    triggers: Optional[str] = None
    reports: list[ReportRow] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    applications_diagram_mermaid: Optional[str] = None


# --- Session schema ---------------------------------------------------------

Mode = Literal["technology_fit", "sdd_builder"]
InputStyle = Literal["drop_in", "chat"]
Phase = Literal["intake", "narrative", "clarification", "ready_to_generate", "generated"]
TriggerType = Literal["scheduled", "manual", "event", "other"]
Criticality = Literal["low", "medium", "high", "critical"]


class Intake(BaseModel):
    project_name: Optional[str] = None
    business_owner: Optional[str] = None
    trigger_type: Optional[TriggerType] = None
    trigger_detail: Optional[str] = None
    frequency: Optional[str] = None
    applications_rough: list[str] = Field(default_factory=list)
    criticality: Optional[Criticality] = None


class ChatMessage(BaseModel):
    role: Literal["assistant", "user"]
    content: str
    ts: str


class CoverageItem(BaseModel):
    id: str
    status: Literal["covered", "partial", "missing"]
    question: Optional[str] = None


class Coverage(BaseModel):
    overall_pct: float
    by_category: dict[str, float] = Field(default_factory=dict)
    items: list[CoverageItem] = Field(default_factory=list)


class Session(BaseModel):
    session_id: str
    mode: Mode
    input_style: InputStyle
    phase: Phase = "intake"
    intake: Optional[Intake] = None
    raw_input: Optional[str] = None
    transcript: list[ChatMessage] = Field(default_factory=list)
    extracted: Optional[Extracted] = None
    coverage: Optional[Coverage] = None
    generated_files: list[str] = Field(default_factory=list)
