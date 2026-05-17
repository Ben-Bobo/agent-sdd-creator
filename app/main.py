from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI(title="Automation SDD Builder")


@app.get("/", response_class=PlainTextResponse)
def root() -> str:
    return "Automation SDD Builder — running"
