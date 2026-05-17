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
from .chat import handle_intake, handle_turn
from .extraction import extract_from_text
from .gap_analysis import analyze as analyze_gaps
from .models import Coverage, Extracted, InputStyle, Intake, Mode, Session
from .sdd_generator import generate_sdd
from .technology_fit import generate_report as generate_tech_fit_report

app = FastAPI(title="Automation SDD Builder")

_BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")
_templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))


class CreateSessionRequest(BaseModel):
    mode: Mode
    input_style: InputStyle


class CreateSessionResponse(BaseModel):
    session_id: str


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(request, "index.html", {})


@app.post("/api/session", response_model=CreateSessionResponse)
def create_session(body: CreateSessionRequest) -> CreateSessionResponse:
    session = session_store.create_session(body.mode, body.input_style)
    return CreateSessionResponse(session_id=session.session_id)


@app.get("/api/session/{session_id}", response_model=Session)
def get_session(session_id: str) -> Session:
    try:
        return session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")


@app.post("/api/dropin", response_model=Extracted)
async def dropin(
    session_id: str = Form(...),
    raw_text: str = Form(""),
    file: UploadFile | None = File(None),
) -> Extracted:
    try:
        session = session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

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
                detail=("Uploaded file is not UTF-8 text. "
                        "Binary formats like .docx aren't supported yet — "
                        "paste the text instead."),
            )
    if not parts:
        raise HTTPException(
            status_code=400, detail="Provide raw_text or a file."
        )

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
        raise HTTPException(status_code=404, detail="Session not found")
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
        raise HTTPException(status_code=404, detail="Session not found")
    if session.phase == "intake":
        raise HTTPException(
            status_code=400,
            detail="Submit /api/intake before chatting.",
        )

    async def event_stream():
        async for chunk in handle_turn(session, body.message):
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        final = {
            "phase": session.phase,
            "coverage_pct": (
                session.coverage.overall_pct if session.coverage else None
            ),
        }
        yield f"event: done\ndata: {json.dumps(final)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/coverage/{session_id}", response_model=Coverage)
def coverage(session_id: str) -> Coverage:
    try:
        session = session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.extracted is None:
        raise HTTPException(
            status_code=400,
            detail="Run extraction first (POST /api/dropin or chat intake).",
        )
    session.coverage = analyze_gaps(session.extracted)
    session_store.save_session(session)
    return session.coverage


@app.post("/api/generate/{session_id}")
def generate(session_id: str) -> dict:
    try:
        session = session_store.load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.extracted is None:
        raise HTTPException(
            status_code=400,
            detail="Run extraction first (POST /api/dropin or chat intake).",
        )

    if session.mode == "sdd_builder":
        files = generate_sdd(session)
    elif session.mode == "technology_fit":
        report = generate_tech_fit_report(session)
        session_dir = _session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "report.md").write_text(report, encoding="utf-8")
        session.generated_files = ["report.md"]
        session.phase = "generated"
        session_store.save_session(session)
        files = session.generated_files
    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {session.mode}")

    return {"files": files}


@app.get("/api/download/{session_id}/{filename}")
def download(session_id: str, filename: str) -> FileResponse:
    if "/" in filename or "\\" in filename or filename.startswith(".."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    session_dir = _session_dir(session_id).resolve()
    target = (session_dir / filename).resolve()
    if not str(target).startswith(str(session_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(target), filename=filename)


def _session_dir(session_id: str) -> Path:
    return Path(os.environ.get("SESSIONS_DIR", "./sessions")) / session_id
