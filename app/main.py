from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from . import session as session_store
from .extraction import extract_from_text
from .models import Extracted, InputStyle, Mode, Session

app = FastAPI(title="Automation SDD Builder")


class CreateSessionRequest(BaseModel):
    mode: Mode
    input_style: InputStyle


class CreateSessionResponse(BaseModel):
    session_id: str


@app.get("/", response_class=PlainTextResponse)
def root() -> str:
    return "Automation SDD Builder — running"


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
