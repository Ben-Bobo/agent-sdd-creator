# curl examples

Start the server first:

```powershell
.\.venv\Scripts\activate
uvicorn app.main:app --reload
```

Then in another shell:

## Create a session

```bash
curl -X POST http://127.0.0.1:8000/api/session ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\": \"sdd_builder\", \"input_style\": \"chat\"}"
```

Response:

```json
{ "session_id": "<uuid>" }
```

On disk: `sessions/<session_id>/state.json` is created and contains the initial Session JSON.

## Fetch a session

```bash
curl http://127.0.0.1:8000/api/session/<session_id>
```

Returns the full Session JSON (mode, input_style, phase, plus empty/null fields ready to be filled in by later tickets).

## Valid values

- `mode`: `technology_fit` | `sdd_builder`
- `input_style`: `drop_in` | `chat`
