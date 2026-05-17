"""Session persistence: JSON files on disk under SESSIONS_DIR/<session_id>/state.json."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from .models import InputStyle, Mode, Session


def _sessions_root() -> Path:
    return Path(os.environ.get("SESSIONS_DIR", "./sessions"))


def _state_path(session_id: str) -> Path:
    return _sessions_root() / session_id / "state.json"


def create_session(mode: Mode, input_style: InputStyle) -> Session:
    session = Session(
        session_id=str(uuid.uuid4()),
        mode=mode,
        input_style=input_style,
    )
    save_session(session)
    return session


def load_session(session_id: str) -> Session:
    return Session.model_validate_json(_state_path(session_id).read_text(encoding="utf-8"))


def save_session(session: Session) -> None:
    path = _state_path(session.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
