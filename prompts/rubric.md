# Developer-ready rubric

For each step in the process, a developer needs to know **all of**:

| Category | What "covered" looks like |
|---|---|
| `trigger` | What kicks this step off — time, event, completion of prior step, or manual user action. |
| `application_screen` | The specific application **and** the screen/page/view (e.g., "SAP ECC → FB60", "Outlook → shared inbox `ap-invoices@`"). |
| `action` | The exact UI action (which button, dropdown value, field) **or** the API endpoint/method if available. |
| `data_inputs` | What data is required, where it comes from, and the format (PDF, JSON, free text, etc.). |
| `data_outputs` | What data is produced and where it goes (DB row, file, downstream system). |
| `decision_logic` | **Business branches** in the normal flow — value-based or count-based forks the process takes deliberately. Must capture the exact condition and threshold ("if amount > $5,000, route to manager"; "if zero matching emails, send alert and stop"). A branch belongs here even if one arm is a no-op or alert. |
| `exception_paths` | **Business process branches for data-state variability** — what the process should do when expected data is missing, empty, or unmatched. Examples: filter returns no rows, lookup finds no match, required field blank on an input row, value is outside an expected enum. **Out of scope** (do NOT include): file corrupt, API/HTTP/library failures, network errors, system downtime, attachment unreadable, email send failed, token refresh — these are developer-handled reliability concerns. Score `covered` if no business-side data-variability branches apply to the step. If a scenario is captured under `decision_logic`, do not repeat it here. |
| `success_criterion` | How the developer / bot knows the step worked. |

For the **process overall**, also required:

| Category | What "covered" looks like |
|---|---|
| `volume_frequency` | How often the process runs and how many items per run. |
| `sla_timing` | How fast the run must complete (e.g., "all invoices posted within 4 hours of receipt"). |
| `access_authentication` | How the bot authenticates: service account, SSO, MFA, credential vault. |
| `compliance_audit` | Required logging, screenshots, approvals, retention. |
| `reporting` | What the business needs to see about runs (success rate, exceptions, throughput) and where. |

## Scoring

- `covered` — explicitly stated, unambiguous, actionable for a developer.
- `partial` — referenced but missing a key detail (e.g., a decision rule mentioned without its threshold).
- `missing` — not addressed at all.

## What's NOT in scope for any category

URL / tenant / server-level detail, credentials, service-account setup, API library implementation specifics, and other automation-platform configuration are **out of scope**. The platform layer already solves these (reusable operations like `send_mail`, `get_mail`, `move_to_folder` are assumed to exist). Do not score those as gaps and do not generate questions about them.
