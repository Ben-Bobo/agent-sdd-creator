from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from . import session as session_store
from .models import InputStyle, Mode, Session

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
