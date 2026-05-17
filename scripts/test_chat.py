"""Scripted end-to-end chat session against /api/intake + /api/chat + /api/generate.

The script plays the role of the chat user — the doer who knows the process.
Run uvicorn separately on port 8765 before invoking this script.
"""

from __future__ import annotations

import json
import sys

import requests

BASE = "http://127.0.0.1:8765"

INTAKE = {
    "project_name": "Vendor Invoice Processing Automation",
    "business_owner": "Sarah Chen — Accounts Payable Lead",
    "trigger_type": "event",
    "trigger_detail": "new email arrival in shared inbox ap-invoices@",
    "frequency": "Continuous throughout the business day (~70-90 invoices/day)",
    "applications_rough": ["Microsoft Outlook (shared mailbox)", "SAP ECC 6.0"],
    "criticality": "high",
}

NARRATIVE_TURNS = [
    "Vendors email PDF invoices to our shared mailbox ap-invoices@. We get 70 to 90 a day, mostly PDFs. Either Jamie or Rohan on my team opens each email, downloads the PDF, eyeballs it for vendor name, invoice number, amount, and line items.",
    "Then they tab over to SAP — we're on ECC 6.0 — and go into transaction FB60 to post it. They look the vendor up in SAP by name. The vendor master is messy and there are duplicates. If they can't find a vendor, they drop the PDF into a 'vendor-not-found' subfolder in the inbox and email the procurement team to set up the vendor.",
    "If the invoice amount is over five thousand dollars, it has to be approved by a manager. So the team enters it in SAP as 'parked' status, then sends an email to the cost center owner — they get the owner's name from the PO if there's one attached, or they ask each other. Once the manager replies with approval, they go back into SAP and post it.",
    "If a PDF is unreadable — bad scan, foreign format — we just reply to the vendor email and ask them to resend. We don't try to fix bad PDFs.",
    "We aim to clear the inbox by end of day. If a day's worth doesn't get posted, vendors can put us on credit hold, so it's pretty high priority. I'd say high business criticality. Sarah Chen runs my team. Once a week I get a summary email with how many were posted automatically vs kicked to my team. That's it — that's the process.",
]

# Canned answers when the AI asks clarifying questions. We pop one off each turn.
CANNED_ANSWERS = [
    "For step 5, they enter transaction code XK03 to look up the vendor, type the vendor name in the Search Term field, click Execute. If multiple results come back they manually pick the closest match.",
    "For the FB60 parking step, they enter Vendor ID, Invoice Date, Reference, Amount, and the GL account from the PO. To park rather than post they go to menu Document → Park.",
    "Approval threshold is exactly $5,000 USD. Anything above gets parked. Approval emails go to whoever owns the cost center listed on the PO.",
    "If the approver doesn't reply within 3 business days, Jamie chases them by email. After 5 days he escalates to me.",
    "Compliance-wise, we have to keep an audit trail of every invoice posted: vendor ID, amount, document number, approver name. Retention is 7 years per finance policy.",
    "The weekly summary email should go out every Monday at 8am. It needs to show count posted, count escalated, and the breakdown of exception reasons.",
]


def _post_json(path: str, body: dict) -> dict:
    r = requests.post(f"{BASE}{path}", json=body, timeout=120)
    r.raise_for_status()
    return r.json()


def _post_chat(session_id: str, message: str) -> tuple[str, dict | None]:
    """Returns (assistant_text, done_event_payload)."""
    url = f"{BASE}/api/chat/{session_id}"
    with requests.post(url, json={"message": message}, stream=True, timeout=600) as r:
        r.raise_for_status()
        assistant_text = ""
        done_payload: dict | None = None
        event_type: str | None = None
        for raw in r.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = raw.strip()
            if not line:
                event_type = None
                continue
            if line.startswith("event:"):
                event_type = line[len("event:") :].strip()
                continue
            if line.startswith("data:"):
                payload = line[len("data:") :].strip()
                if not payload:
                    continue
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if event_type == "done":
                    done_payload = obj
                else:
                    assistant_text += obj.get("text", "")
        return assistant_text, done_payload


def main() -> int:
    print("=== Create session ===")
    sess = _post_json("/api/session", {"mode": "sdd_builder", "input_style": "chat"})
    session_id = sess["session_id"]
    print(f"  session_id: {session_id}")

    print("\n=== Submit intake ===")
    intake_resp = _post_json("/api/intake", {"session_id": session_id, "intake": INTAKE})
    print(f"  phase after intake: {intake_resp['phase']}")
    print(f"  opening prompt: {intake_resp['opening_prompt'][:80]}...")

    print("\n=== Narrative turns ===")
    for i, turn in enumerate(NARRATIVE_TURNS, start=1):
        print(f"\nUser turn {i}: {turn[:80]}...")
        assistant, done = _post_chat(session_id, turn)
        print(
            f"AI ({done['phase'] if done else '?'}, cov={done.get('coverage_pct') if done else '?'}):"
        )
        print(f"  {assistant[:200]}{'...' if len(assistant) > 200 else ''}")
        if done and done["phase"] == "ready_to_generate":
            print("\n** AI signals ready to generate — stopping the narrative loop **")
            break

    # Force transition to clarification if narrative classifier hasn't done it yet.
    sess_state = requests.get(f"{BASE}/api/session/{session_id}", timeout=30).json()
    if sess_state["phase"] == "narrative":
        print("\n=== Saying 'that's it' to force transition ===")
        assistant, done = _post_chat(session_id, "that's it")
        print(
            f"AI ({done['phase'] if done else '?'}, cov={done.get('coverage_pct') if done else '?'}):"
        )
        print(f"  {assistant[:200]}{'...' if len(assistant) > 200 else ''}")

    print("\n=== Clarification turns (canned answers) ===")
    for i, answer in enumerate(CANNED_ANSWERS, start=1):
        sess_state = requests.get(f"{BASE}/api/session/{session_id}", timeout=30).json()
        if sess_state["phase"] not in ("clarification", "narrative"):
            print(f"\n** Phase is {sess_state['phase']} — stopping clarification loop **")
            break
        print(f"\nUser canned answer {i}: {answer[:80]}...")
        assistant, done = _post_chat(session_id, answer)
        print(
            f"AI ({done['phase'] if done else '?'}, cov={done.get('coverage_pct') if done else '?'}):"
        )
        print(f"  {assistant[:200]}{'...' if len(assistant) > 200 else ''}")

    print("\n=== Final session state ===")
    sess_state = requests.get(f"{BASE}/api/session/{session_id}", timeout=30).json()
    print(f"  phase: {sess_state['phase']}")
    cov = sess_state.get("coverage") or {}
    print(f"  overall_pct: {cov.get('overall_pct')}")
    ex = sess_state.get("extracted") or {}
    print(f"  steps: {len(ex.get('steps') or [])}")
    print(f"  applications: {[a['name'] for a in ex.get('applications') or []]}")

    print("\n=== Generate SDD ===")
    gen = _post_json(f"/api/generate/{session_id}", {})
    print(f"  files: {gen['files']}")
    print(f"  session dir: sessions/{session_id}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
