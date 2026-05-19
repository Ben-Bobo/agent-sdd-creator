"""Chat state machine + streaming.

Phases: intake -> narrative -> clarification -> ready_to_generate -> generated.

Per-turn extraction is gone. Instead, when the user signals they're done
describing the process (explicit "that's it" or the done classifier fires),
we run extraction + gap-analysis **once** to build a cursor of specific gaps
to fill, then walk through them one per turn. Each clarification turn does
a small validate-and-advance LLM call: if the user's answer satisfies the
current gap's rubric category, the cursor advances; otherwise we re-ask
with a more pointed follow-up, up to two attempts before force-advancing.

The single ANALYZE step at the narrative→clarification transition is the
only slow phase. Per clarification turn = one small Sonnet call (~3-5s).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from pydantic import BaseModel

from . import session as session_store
from .extraction import extract_from_text
from .gap_analysis import analyze as analyze_gaps
from .llm import complete, complete_json
from .models import (
    Application,
    ChatMessage,
    ClarificationGap,
    CoverageItem,
    Extracted,
    Intake,
    Session,
)
from .prompts import load_prompt


class _ValidationResult(BaseModel):
    satisfied: bool
    also_satisfies: list[str]
    follow_up: str


class _ConsolidationItem(BaseModel):
    primary_id: str
    primary_category: str
    merged_question: str
    source_ids: list[str]


class _Consolidation(BaseModel):
    items: list[_ConsolidationItem]


_MAX_ATTEMPTS_PER_GAP = 2

# How many upcoming gaps to include in the validator's lookahead window.
# Keeps the prompt small while catching the common "one answer covers
# several related gaps" case.
_LOOKAHEAD_GAPS = 5

# Skip the consolidation pass when there are few gaps — not worth the cost
# or risk of accidental merges.
_CONSOLIDATE_MIN_GAPS = 4

OPENING_PROMPT = (
    "Walk me through the process from start to finish. Be as specific as you can "
    "when you describe the steps, but don't worry if you miss something. I'll "
    "ask follow-up questions after."
)

NARRATIVE_ACK = "Got it, keep going. What happens next?"

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
    )
    session.phase = "narrative"
    session.transcript.append(ChatMessage(role="assistant", content=OPENING_PROMPT, ts=_now()))
    session_store.save_session(session)


async def handle_turn(session: Session, user_message: str) -> AsyncIterator[tuple[str, str]]:
    """Process a user turn. Yields ``(kind, payload)`` tuples where ``kind``
    is ``"status"`` (a short label of the current backend step, for the UI)
    or ``"content"`` (an assistant text chunk to append to the response)."""
    session.transcript.append(ChatMessage(role="user", content=user_message, ts=_now()))

    # Phase transitions.
    if session.phase == "narrative":
        if _is_explicit_done(user_message) or _classify_user_done(session.transcript):
            session.phase = "clarification"
    elif session.phase == "clarification":
        # User can bail out of clarification with "I'm done"; remaining
        # gaps will show up as TBDs in the final SDD.
        if _is_explicit_done(user_message):
            session.phase = "ready_to_generate"

    assistant_text = ""

    if session.phase == "narrative":
        assistant_text = NARRATIVE_ACK
        for word in _word_chunks(NARRATIVE_ACK):
            yield "content", word

    elif session.phase == "clarification":
        if not session.clarification_cursor:
            # First entry into clarification: run the one big analysis pass
            # and build the gap cursor.
            async for ev in _run_initial_analysis(session):
                yield ev
            if session.phase == "ready_to_generate":
                # Analysis found nothing to ask — go straight to ready.
                assistant_text = READY_MESSAGE
                for word in _word_chunks(READY_MESSAGE):
                    yield "content", word
            else:
                # Stream the first un-satisfied gap's question. Position may
                # already be past 0 if narrative covered the leading gaps.
                first_q = session.clarification_cursor[
                    session.clarification_position
                ].item.question
                assistant_text = first_q
                for word in _word_chunks(first_q):
                    yield "content", word
        else:
            # Subsequent clarification turn: validate the user's answer
            # against the current gap, then advance or re-ask.
            next_question = await _advance_cursor(session, user_message)
            if session.phase == "ready_to_generate":
                assistant_text = READY_MESSAGE
                for word in _word_chunks(READY_MESSAGE):
                    yield "content", word
            else:
                assistant_text = next_question
                for word in _word_chunks(next_question):
                    yield "content", word

    elif session.phase == "ready_to_generate":
        assistant_text = READY_MESSAGE
        for word in _word_chunks(READY_MESSAGE):
            yield "content", word

    session.transcript.append(ChatMessage(role="assistant", content=assistant_text, ts=_now()))
    session_store.save_session(session)


async def _run_initial_analysis(session: Session) -> AsyncIterator[tuple[str, str]]:
    """At the narrative→clarification transition: run Sonnet extraction +
    gap-analysis once, consolidate near-duplicate questions, then build the
    cursor of gaps to walk through."""
    yield "status", "Reviewing what you told me — this may take a minute"
    chat_context = _build_chat_context(session)
    session.extracted = extract_from_text(chat_context)
    yield "status", "Figuring out what's still missing"
    session.coverage = analyze_gaps(session.extracted, raw_input=chat_context)

    raw_gaps = [item for item in session.coverage.items if item.status != "covered"]

    if len(raw_gaps) >= _CONSOLIDATE_MIN_GAPS:
        yield "status", "Tidying up the question list"
        consolidated = _consolidate_gaps(raw_gaps)
    else:
        consolidated = raw_gaps

    session.clarification_cursor = [ClarificationGap(item=item) for item in consolidated]
    session.clarification_position = 0

    # Skip any leading gaps the user already answered during narrative.
    cursor = session.clarification_cursor
    while session.clarification_position < len(cursor):
        nxt = cursor[session.clarification_position]
        if not _is_already_answered(nxt.item, session.transcript):
            break
        nxt.final_status = "satisfied"
        session.clarification_position += 1

    if session.clarification_position >= len(cursor):
        session.phase = "ready_to_generate"


def _consolidate_gaps(items: list[CoverageItem]) -> list[CoverageItem]:
    """Run a Sonnet pass that merges near-duplicate questions across the full
    gap list. Returns a new list of CoverageItem with merged questions and
    representative ids. Defensively re-adds any items the LLM dropped."""
    body_lines = ["## Gaps to consolidate", ""]
    for it in items:
        body_lines.append(f"- id: {it.id} | category: {it.category}")
        body_lines.append(f"  question: {it.question}")
    body = "\n".join(body_lines)

    try:
        result = complete_json(
            system=load_prompt("consolidate_gaps"),
            messages=[{"role": "user", "content": body}],
            schema=_Consolidation,
            model=os.environ["MODEL_MAIN"],
            max_tokens=4096,
        )
    except Exception:
        # If consolidation fails for any reason, fall back to the original
        # list — losing dedupe is harmless; losing gaps would not be.
        return items

    original_by_id = {it.id: it for it in items}
    covered: set[str] = set()
    out: list[CoverageItem] = []

    for group in result.items:
        valid_sources = [sid for sid in group.source_ids if sid in original_by_id]
        if not valid_sources:
            continue
        primary_id = (
            group.primary_id if group.primary_id in valid_sources else valid_sources[0]
        )
        primary_src = original_by_id[primary_id]
        out.append(
            CoverageItem(
                id=primary_id,
                category=group.primary_category or primary_src.category,
                status=primary_src.status,
                question=group.merged_question or primary_src.question,
            )
        )
        covered.update(valid_sources)

    # Safety net: any input id the LLM forgot to assign to a group gets
    # added back as its own singleton entry. Better to ask twice than to
    # silently drop a gap from the SDD.
    for it in items:
        if it.id not in covered:
            out.append(it)

    return out


async def _advance_cursor(session: Session, user_message: str) -> str:
    """Validate the user's reply against the current gap (and a small
    lookahead window). Mark any gaps the answer covered as satisfied and
    advance the cursor past them. On a not-satisfied current gap, return a
    drilled-down re-ask. Force-advance after _MAX_ATTEMPTS_PER_GAP. Sets
    ``session.phase = "ready_to_generate"`` when the cursor is exhausted."""
    cursor = session.clarification_cursor
    pos = session.clarification_position
    if pos >= len(cursor):
        session.phase = "ready_to_generate"
        return READY_MESSAGE

    current = cursor[pos]
    step_summary = _resolve_step_summary(current.item.id, session.extracted)
    lookahead = [
        gap.item
        for gap in cursor[pos + 1 : pos + 1 + _LOOKAHEAD_GAPS]
        if gap.final_status is None
    ]
    result = _validate_answer(current.item, user_message, step_summary, lookahead)

    if result.satisfied:
        current.final_status = "satisfied"
        # Mark any lookahead gaps the same answer also covered.
        also = set(result.also_satisfies)
        if also:
            for gap in cursor[pos + 1 : pos + 1 + _LOOKAHEAD_GAPS]:
                if gap.item.id in also and gap.final_status is None:
                    gap.final_status = "satisfied"
        # Skip past every contiguous satisfied gap starting from pos+1.
        new_pos = pos + 1
        while new_pos < len(cursor) and cursor[new_pos].final_status is not None:
            new_pos += 1
        session.clarification_position = new_pos
    else:
        current.attempts += 1
        if current.attempts >= _MAX_ATTEMPTS_PER_GAP:
            current.final_status = "unresolved"
            session.clarification_position += 1
        else:
            # Stay on this gap, re-ask with the drilled-down follow-up.
            return result.follow_up or current.item.question

    # Before asking the next gap, scan the full transcript: if the user
    # already answered it in an earlier turn (e.g., named a column when
    # listing fields, and the next gap asks about that column), skip.
    while session.clarification_position < len(cursor):
        nxt = cursor[session.clarification_position]
        if nxt.final_status is not None:
            session.clarification_position += 1
            continue
        if not _is_already_answered(nxt.item, session.transcript):
            break
        nxt.final_status = "satisfied"
        session.clarification_position += 1

    if session.clarification_position >= len(cursor):
        session.phase = "ready_to_generate"
        return READY_MESSAGE
    return cursor[session.clarification_position].item.question


def _is_already_answered(gap_item: CoverageItem, transcript: list[ChatMessage]) -> bool:
    """Cheap Haiku check: does the transcript already answer this question?
    Biased toward False — only returns True when the answer is plainly
    present, so we don't accidentally skip real gaps."""
    if not transcript:
        return False
    body_lines = [f"Question: {gap_item.question}", "", "Transcript:"]
    for m in transcript:
        body_lines.append(f"{m.role}: {m.content}")
    result = complete(
        system=load_prompt("already_answered"),
        messages=[{"role": "user", "content": "\n".join(body_lines)}],
        model=os.environ["MODEL_CHEAP"],
        max_tokens=4,
    )
    return result.strip().lower().startswith("y")


def _validate_answer(
    gap_item: CoverageItem,
    user_message: str,
    step_summary: str | None,
    lookahead: list[CoverageItem],
) -> _ValidationResult:
    system = load_prompt("clarification_step") + "\n\n---\n\n" + load_prompt("rubric")
    parts: list[str] = [
        "## Current gap (the one we just asked about)",
        f"- id: {gap_item.id}",
        f"- category: {gap_item.category}",
        f"- question we asked: {gap_item.question}",
        f"- step summary: {step_summary or '(process-wide, not step-specific)'}",
        "",
    ]
    if lookahead:
        parts.append("## Upcoming gaps (check if the user's answer also covers any of these)")
        for item in lookahead:
            parts.append(f"- id: {item.id} | category: {item.category}")
            parts.append(f"  question: {item.question}")
        parts.append("")
    parts.append("## User's latest answer")
    parts.append(user_message)
    return complete_json(
        system=system,
        messages=[{"role": "user", "content": "\n".join(parts)}],
        schema=_ValidationResult,
        model=os.environ["MODEL_MAIN"],
        max_tokens=600,
    )


def _resolve_step_summary(gap_id: str, extracted: Extracted | None) -> str | None:
    """Look up a step's summary by parsing the gap id (e.g., ``step_3.action``).
    Returns None for ``overall.*`` items or when the step can't be found."""
    if extracted is None or not gap_id.startswith("step_"):
        return None
    try:
        n = int(gap_id.split(".", 1)[0].removeprefix("step_"))
    except ValueError:
        return None
    for step in extracted.steps:
        if step.number == n:
            return step.summary
    return None


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


def _word_chunks(text: str):
    """Yield word-by-word so the SSE stream feels live for hardcoded messages."""
    words = text.split(" ")
    for i, w in enumerate(words):
        yield w + (" " if i < len(words) - 1 else "")
