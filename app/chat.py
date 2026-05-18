"""Chat state machine + streaming.

Phases: intake -> narrative -> clarification -> ready_to_generate -> generated.

After each user turn we *may* re-extract on (intake + transcript) and re-run
gap analysis so the coverage indicator stays current. To avoid paying for
that on acknowledgement-only turns ("ok", "yes", "no nothing else"), a cheap
Haiku classifier first judges whether the reply added new process detail.
If not, we reuse the previous Extracted + Coverage unchanged.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

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
    "done",
    "that's it",
    "thats it",
    "i'm done",
    "im done",
    "no more",
    "nothing else",
    "that's all",
    "thats all",
    "that covers it",
    "i think that's it",
}

COVERAGE_AUTO_THRESHOLD = 0.85


def handle_intake(session: Session, intake_data: Intake) -> None:
    """Store Phase 1 answers, seed Extracted, transition to narrative,
    append the opening assistant prompt to the transcript."""
    session.intake = intake_data
    session.extracted = Extracted(
        project_name=intake_data.project_name or "Unspecified",
        summary="Captured during chat (pending narrative).",
        business_owner=intake_data.business_owner or "",
        document_processing=[],
        artificial_intelligence=[],
        credential_management="",
        tool_selection_rationale="",
        business_criticality=intake_data.criticality or "",
        complexity_score="",
        applications=[
            Application(
                name=a,
                version="",
                language="",
                environment="",
                access_method="",
                notes="",
            )
            for a in (intake_data.applications_rough or [])
            if a
        ],
        known_errors=[],
        accepted_failure_threshold="",
        rerun_on_failure="",
        schedule_frequency=intake_data.frequency or "",
        bot_utilization_pct="",
        triggers=_format_trigger(intake_data),
        reports=[],
        steps=[],
        applications_diagram_mermaid="",
        design_improvements=[],
    )
    session.phase = "narrative"
    session.transcript.append(ChatMessage(role="assistant", content=OPENING_PROMPT, ts=_now()))
    session_store.save_session(session)


async def handle_turn(session: Session, user_message: str) -> AsyncIterator[tuple[str, str]]:
    """Process a user turn. Yields ``(kind, payload)`` tuples where ``kind``
    is ``"status"`` (a short label of the current backend step, for the UI)
    or ``"content"`` (an assistant text chunk to append to the response)."""
    session.transcript.append(ChatMessage(role="user", content=user_message, ts=_now()))

    if _has_new_detail(session.transcript):
        yield "status", "Updating my notes"
        session.extracted = extract_from_text(_build_chat_context(session))
        yield "status", "Checking what's still missing"
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
            yield "content", word
    elif session.phase == "ready_to_generate":
        assistant_text = READY_MESSAGE
        for word in _word_chunks(READY_MESSAGE):
            yield "content", word
    elif session.phase == "clarification":
        yield "status", "Thinking of a follow-up"
        system = load_prompt("system_chat") + "\n\n---\n\n" + load_prompt("clarifier_question")
        context_body = _build_clarifier_context(session)
        async for chunk in stream(
            system=system,
            messages=[{"role": "user", "content": context_body}],
            model=os.environ["MODEL_MAIN"],
            max_tokens=300,
        ):
            assistant_text += chunk
            yield "content", chunk
        assistant_text = assistant_text.strip()

    session.transcript.append(ChatMessage(role="assistant", content=assistant_text, ts=_now()))
    session_store.save_session(session)


def _now() -> str:
    return datetime.now(UTC).isoformat()


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


def _has_new_detail(transcript: list[ChatMessage]) -> bool:
    """Cheap classifier: did the user's last turn add process info worth
    re-extracting on? Defaults to True when there's no prior assistant turn
    to anchor the judgment against."""
    if not transcript or transcript[-1].role != "user":
        return True
    last_user = transcript[-1].content
    prior_assistant = next(
        (m.content for m in reversed(transcript[:-1]) if m.role == "assistant"),
        None,
    )
    if prior_assistant is None:
        return True
    body = f"assistant: {prior_assistant}\nuser: {last_user}"
    result = complete(
        system=load_prompt("has_new_detail"),
        messages=[{"role": "user", "content": body}],
        model=os.environ["MODEL_CHEAP"],
        max_tokens=4,
    )
    return not result.strip().lower().startswith("n")


def _format_trigger(intake: Intake) -> str:
    parts = [p for p in (intake.trigger_type, intake.trigger_detail) if p]
    return " — ".join(parts) if parts else ""


def _build_chat_context(session: Session) -> str:
    lines: list[str] = []
    if session.intake:
        lines.append("# Phase 1 intake answers")
        intake = session.intake
        lines.append(f"- Project name: {intake.project_name}")
        lines.append(f"- Business owner: {intake.business_owner}")
        if intake.trigger_type or intake.trigger_detail:
            lines.append(f"- Trigger: {intake.trigger_type or ''} — {intake.trigger_detail or ''}")
        if intake.frequency:
            lines.append(f"- Frequency: {intake.frequency}")
        if intake.applications_rough:
            lines.append(f"- Applications mentioned: {', '.join(intake.applications_rough)}")
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
