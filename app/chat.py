"""Chat state machine + streaming.

Phases: intake -> narrative -> clarification -> ready_to_generate -> generated.

After each user turn we re-extract on (intake + transcript) and re-run gap
analysis, so the coverage indicator updates in real time. That is intentionally
expensive — fine for v1, optimize later.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import AsyncIterator

from . import session as session_store
from .extraction import extract_from_text
from .gap_analysis import analyze as analyze_gaps
from .llm import complete, stream
from .models import Application, ChatMessage, Extracted, Intake, Session
from .prompts import load_prompt

OPENING_PROMPT = (
    "Walk me through the process from start to finish. Don't worry about "
    "perfection — describe it the way you'd explain it to a coworker. I'll "
    "ask follow-up questions after."
)

NARRATIVE_ACK = "Got it — keep going. What happens next?"

READY_MESSAGE = (
    "That gives me enough to draft the SDD. Click **Generate Draft** when "
    "you're ready, or keep adding detail if there's more."
)

EXPLICIT_DONE_PHRASES = {
    "done", "that's it", "thats it", "i'm done", "im done",
    "no more", "nothing else", "that's all", "thats all",
    "that covers it", "i think that's it",
}

COVERAGE_AUTO_THRESHOLD = 0.85


def handle_intake(session: Session, intake_data: Intake) -> None:
    """Store Phase 1 answers, seed Extracted, transition to narrative,
    append the opening assistant prompt to the transcript."""
    session.intake = intake_data
    session.extracted = Extracted(
        project_name=intake_data.project_name or "Unspecified",
        summary="Captured during chat (pending narrative).",
        business_owner=intake_data.business_owner,
        business_criticality=intake_data.criticality,
        schedule_frequency=intake_data.frequency,
        triggers=_format_trigger(intake_data),
        applications=[
            Application(name=a) for a in (intake_data.applications_rough or []) if a
        ],
    )
    session.phase = "narrative"
    session.transcript.append(
        ChatMessage(role="assistant", content=OPENING_PROMPT, ts=_now())
    )
    session_store.save_session(session)


async def handle_turn(session: Session, user_message: str) -> AsyncIterator[str]:
    """Process a user turn and yield assistant response chunks (for SSE)."""
    session.transcript.append(
        ChatMessage(role="user", content=user_message, ts=_now())
    )

    session.extracted = extract_from_text(_build_chat_context(session))
    session.coverage = analyze_gaps(session.extracted)

    if session.phase == "narrative":
        if _is_explicit_done(user_message) or _classify_user_done(session.transcript):
            session.phase = "clarification"

    if session.coverage and session.coverage.overall_pct >= COVERAGE_AUTO_THRESHOLD:
        session.phase = "ready_to_generate"

    assistant_text = ""

    if session.phase == "narrative":
        assistant_text = NARRATIVE_ACK
        for word in _word_chunks(NARRATIVE_ACK):
            yield word
    elif session.phase == "ready_to_generate":
        assistant_text = READY_MESSAGE
        for word in _word_chunks(READY_MESSAGE):
            yield word
    elif session.phase == "clarification":
        system = (
            load_prompt("system_chat")
            + "\n\n---\n\n"
            + load_prompt("clarifier_question")
        )
        context_body = _build_clarifier_context(session)
        async for chunk in stream(
            system=system,
            messages=[{"role": "user", "content": context_body}],
            model=os.environ["MODEL_MAIN"],
            max_tokens=300,
        ):
            assistant_text += chunk
            yield chunk
        assistant_text = assistant_text.strip()

    session.transcript.append(
        ChatMessage(role="assistant", content=assistant_text, ts=_now())
    )
    session_store.save_session(session)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_explicit_done(msg: str) -> bool:
    normalized = msg.strip().lower().rstrip(".!,?")
    return normalized in EXPLICIT_DONE_PHRASES


def _classify_user_done(transcript: list[ChatMessage]) -> bool:
    if len(transcript) < 4:
        return False
    body = "\n".join(f"{m.role}: {m.content}" for m in transcript)
    result = complete(
        system=load_prompt("is_user_done"),
        messages=[{"role": "user", "content": body}],
        model=os.environ["MODEL_CHEAP"],
        max_tokens=4,
    )
    return result.strip().lower().startswith("y")


def _format_trigger(intake: Intake) -> str | None:
    parts = [p for p in (intake.trigger_type, intake.trigger_detail) if p]
    return " — ".join(parts) if parts else None


def _build_chat_context(session: Session) -> str:
    lines: list[str] = []
    if session.intake:
        lines.append("# Phase 1 intake answers")
        intake = session.intake
        lines.append(f"- Project name: {intake.project_name}")
        lines.append(f"- Business owner: {intake.business_owner}")
        if intake.trigger_type or intake.trigger_detail:
            lines.append(
                f"- Trigger: {intake.trigger_type or ''} — {intake.trigger_detail or ''}"
            )
        if intake.frequency:
            lines.append(f"- Frequency: {intake.frequency}")
        if intake.applications_rough:
            lines.append(
                f"- Applications mentioned: {', '.join(intake.applications_rough)}"
            )
        if intake.criticality:
            lines.append(f"- Business criticality: {intake.criticality}")
        lines.append("")
    lines.append("# Chat transcript")
    for msg in session.transcript:
        lines.append(f"## {msg.role}")
        lines.append(msg.content)
        lines.append("")
    return "\n".join(lines)


def _build_clarifier_context(session: Session) -> str:
    parts: list[str] = []
    if session.extracted is not None:
        parts.append("## Extracted (current snapshot)")
        parts.append(session.extracted.model_dump_json(indent=2))
        parts.append("")
    if session.coverage is not None:
        parts.append("## Coverage (current gaps)")
        parts.append(session.coverage.model_dump_json(indent=2))
        parts.append("")
    parts.append("## Recent transcript")
    for msg in session.transcript[-10:]:
        parts.append(f"**{msg.role}**: {msg.content}")
    return "\n".join(parts)


def _word_chunks(text: str):
    """Yield word-by-word so the SSE stream feels live for hardcoded messages."""
    words = text.split(" ")
    for i, w in enumerate(words):
        yield w + (" " if i < len(words) - 1 else "")
