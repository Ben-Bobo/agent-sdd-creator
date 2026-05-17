# Sample output

Real, unedited output from two runs of the app. Open these to see what the tool produces without having to clone, install, and run it yourself. Names in the examples are fictional.

## `sdd_invoice_processing/`

**Mode:** SDD Builder · **Input style:** Drop-in
**Source:** a one-page kickoff meeting transcript between a business analyst and an accounts-payable lead.

| File | What it is |
| --- | --- |
| `input.md` | The meeting transcript fed into the tool. |
| `sdd.docx` | The filled-out Software Design Document the tool produced. Open in Word. |
| `applications_diagram.png` | The applications/systems diagram embedded inside `sdd.docx`. |
| `applications_diagram.mmd` | Mermaid source for the diagram, in case a developer wants to tweak it. |
| `gaps.md` | Follow-up questions for the business — gaps the tool wasn't confident about, grouped by step. |

The transcript covers the happy path and a couple of exception paths but leaves a lot unsaid (exact SAP field sequence, retry behavior on errors, approval timeouts). `gaps.md` is the artifact the operator forwards to the business to close those.

## `technology_fit_vague_request/`

**Mode:** Technology Fit · **Input style:** Drop-in
**Source:** a three-line email from a finance director asking "can we automate this?"

| File | What it is |
| --- | --- |
| `input.md` | The original email. |
| `report.md` | The tool's recommendation. |

This sample shows how the tool behaves when the input is too thin to commit to a recommendation: it says so plainly, lists the blockers, and suggests the conversation that needs to happen before anyone builds anything.
