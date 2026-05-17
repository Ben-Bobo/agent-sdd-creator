# Developer-ready rubric

For each step in the process, a developer needs to know **all of**:

| Category | What "covered" looks like |
|---|---|
| `trigger` | What kicks this step off — time, event, completion of prior step, or manual user action. |
| `application_screen` | The specific application **and** the screen/page/view (e.g., "SAP ECC → FB60", "Outlook → shared inbox `ap-invoices@`"). |
| `action` | The exact UI action (which button, dropdown value, field) **or** the API endpoint/method if available. |
| `data_inputs` | What data is required, where it comes from, and the format (PDF, JSON, free text, etc.). |
| `data_outputs` | What data is produced and where it goes (DB row, file, downstream system). |
| `decision_logic` | Any conditional rule. Must capture the **exact condition and threshold** ("if amount > $5,000, route to manager"), not a paraphrase. |
| `exception_paths` | What happens on failure: system down, data missing, action fails, user denies, etc. |
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
