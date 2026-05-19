# ruff: noqa: E402  -- load_dotenv() must run before modules that read env vars at import time
import os
import shutil

from dotenv import load_dotenv

load_dotenv()

_mmdc = os.environ.get("MERMAID_CLI", "mmdc")
if shutil.which(_mmdc) is None:
    raise RuntimeError(
        f"Mermaid CLI '{_mmdc}' not found on PATH. "
        "Install with: npm install -g @mermaid-js/mermaid-cli"
    )

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import session as session_store
from .chat import _build_chat_context, handle_intake, handle_turn, skip_current_gap
from .extraction import extract_from_text
from .gap_analysis import analyze as analyze_gaps
from .models import Coverage, Extracted, InputStyle, Intake, Session
from .sdd_generator import generate_sdd

app = FastAPI(title="Automation SDD Builder")

_BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")
_templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))


class CreateSessionRequest(BaseModel):
    input_style: InputStyle


class CreateSessionResponse(BaseModel):
    session_id: str


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(
        request,
        "index.html",
        {
            "contact_email": os.environ.get(
                "BOT_CONTROLLER_EMAIL", "rpa.botcontroller@cbrands.com"
            ),
        },
    )


@app.post("/api/session", response_model=CreateSessionResponse)
def create_session(body: CreateSessionRequest) -> CreateSessionResponse:
    session = session_store.create_session(body.input_style)
    return CreateSessionResponse(session_id=session.session_id)


@app.get("/api/session/{session_id}", response_model=Session)
def get_session(session_id: str) -> Session:
    try:
        return session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None


@app.post("/api/dropin", response_model=Extracted)
async def dropin(
    session_id: str = Form(...),
    raw_text: str = Form(""),
    file: UploadFile | None = File(None),
) -> Extracted:
    try:
        session = session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None

    parts: list[str] = []
    if raw_text.strip():
        parts.append(raw_text)
    if file is not None:
        blob = await file.read()
        try:
            parts.append(blob.decode("utf-8"))
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Uploaded file is not UTF-8 text. "
                    "Binary formats like .docx aren't supported yet — "
                    "paste the text instead."
                ),
            ) from None
    if not parts:
        raise HTTPException(status_code=400, detail="Provide raw_text or a file.")

    combined = "\n\n".join(parts)
    session.raw_input = combined
    session.extracted = extract_from_text(combined)
    session_store.save_session(session)
    return session.extracted


class IntakeRequest(BaseModel):
    session_id: str
    intake: Intake


class ChatRequest(BaseModel):
    message: str


@app.post("/api/intake")
def intake(body: IntakeRequest) -> dict:
    try:
        session = session_store.load_session(body.session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    handle_intake(session, body.intake)
    return {
        "phase": session.phase,
        "opening_prompt": session.transcript[-1].content if session.transcript else None,
    }


@app.post("/api/chat/{session_id}")
async def chat(session_id: str, body: ChatRequest) -> StreamingResponse:
    try:
        session = session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    if session.phase == "intake":
        raise HTTPException(
            status_code=400,
            detail="Submit /api/intake before chatting.",
        )

    async def event_stream():
        async for kind, payload in handle_turn(session, body.message):
            if kind == "status":
                yield f"event: status\ndata: {json.dumps({'text': payload})}\n\n"
            else:
                yield f"data: {json.dumps({'text': payload})}\n\n"
        final = {
            "phase": session.phase,
            "coverage_pct": (session.coverage.overall_pct if session.coverage else None),
            "clarification_progress": (
                {
                    "position": session.clarification_position,
                    "total": len(session.clarification_cursor),
                }
                if session.clarification_cursor
                else None
            ),
        }
        yield f"event: done\ndata: {json.dumps(final)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class SkipResponse(BaseModel):
    text: str
    phase: str
    clarification_progress: dict | None = None


@app.post("/api/chat/{session_id}/skip", response_model=SkipResponse)
def skip_clarification(session_id: str) -> SkipResponse:
    try:
        session = session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    if session.phase != "clarification":
        raise HTTPException(
            status_code=400, detail="Skip is only available during clarification."
        )
    text = skip_current_gap(session)
    progress = (
        {
            "position": session.clarification_position,
            "total": len(session.clarification_cursor),
        }
        if session.clarification_cursor
        else None
    )
    return SkipResponse(text=text, phase=session.phase, clarification_progress=progress)


@app.post("/api/coverage/{session_id}", response_model=Coverage)
def coverage(session_id: str) -> Coverage:
    try:
        session = session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    if session.extracted is None:
        raise HTTPException(
            status_code=400,
            detail="Run extraction first (POST /api/dropin or chat intake).",
        )
    raw_input_for_gaps = session.raw_input
    if raw_input_for_gaps is None and session.input_style == "chat":
        raw_input_for_gaps = _build_chat_context(session)
    session.coverage = analyze_gaps(session.extracted, raw_input=raw_input_for_gaps)
    session_store.save_session(session)
    return session.coverage


@app.post("/api/generate/{session_id}")
def generate(session_id: str) -> StreamingResponse:
    try:
        session = session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    if session.extracted is None:
        raise HTTPException(
            status_code=400,
            detail="Run extraction first (POST /api/dropin or chat intake).",
        )

    def event_stream():
        for kind, value in generate_sdd(session):
            if kind == "status":
                yield f"event: status\ndata: {json.dumps({'text': value})}\n\n"
            elif kind == "done":
                yield f"event: done\ndata: {json.dumps({'files': value})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/download/{session_id}/{filename}")
def download(session_id: str, filename: str) -> FileResponse:
    if "/" in filename or "\\" in filename or filename.startswith(".."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    sdir = session_store.session_dir(session_id).resolve()
    target = (sdir / filename).resolve()
    if not str(target).startswith(str(sdir)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(target), filename=filename)
