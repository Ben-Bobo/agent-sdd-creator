# SDD Template Token Reference

The docx template at `templates/Automation_SDD_template.docx` uses `{{token}}` placeholders that `app/docx_filler.py` replaces from the `Extracted` object. This doc is the **source of truth** for token names — keep it in sync with `Extracted` (see `app/models.py`).

Conventions:
- Scalar tokens: `{{token}}` — replaced with a single value; lists are joined with `; `.
- **Repeating-row tokens** use a dotted prefix (`{{app.name}}`, `{{err.action}}`, `{{report.report_type}}`). The filler finds the table row containing those tokens, clones it once per item in the matching list, and removes the original template row.
- Missing values are rendered as `[TBD - <reason>]` so gaps surface in the doc itself.

## Section 1 — Project metadata (Table 0)

| Cell label | Token | Source |
|---|---|---|
| Project Name | `{{project_name}}` | `Extracted.project_name` |
| Jira Project # | `{{jira_project}}` | (not extracted — defaults to TBD) |

## Section 2 — Automation toolset (Table 1)

| Cell label | Token | Source |
|---|---|---|
| Automation Tools | `{{automation_tools}}` | (not extracted — defaults to TBD) |
| BTP Services | `{{btp_services}}` | (not extracted — defaults to TBD) |
| Document Processing | `{{document_processing}}` | `Extracted.document_processing[]` |
| New SDKs/Objects | `{{new_sdks_objects}}` | (not extracted — defaults to TBD) |
| Artificial Intelligence | `{{artificial_intelligence}}` | `Extracted.artificial_intelligence[]` (set by narrative pass; usually `[]`) |
| Credential Management | `{{credential_management}}` | `Extracted.credential_management` |

## Section 3 — Tool selection rationale (Table 2)

Free-text cell, replace its content with `{{tool_selection_rationale}}`. No longer auto-generated — renders as `[TBD - populate manually]`.

## Section 4 — Project posture (Table 3)

| Cell label | Token | Source |
|---|---|---|
| Business Criticality | `{{business_criticality}}` | `Extracted.business_criticality` |
| Development Complexity Score | `{{complexity_score}}` | `Extracted.complexity_score` |

## Section 5 — Applications used (Table 4, repeating)

Header row stays as-is. The **one template row** below the header contains:

| Application Name | Version | Application Language | Environment/Access | Comments |
|---|---|---|---|---|
| `{{app.name}}` | (blank) | (blank) | `{{app.environment}}` | `{{app.notes}}` |

Source: `Extracted.applications[]`. The Version and Application Language columns are intentionally not populated by this tool — those cells are blank in the template. Any extra empty rows in the operator's original docx are removed during tokenization.

## Section 6 — Known errors and exceptions (Table 5, repeating)

| Error/Exception Name | Action | Parameters | Action to be taken |
|---|---|---|---|
| `{{err.name}}` | `{{err.action}}` | `{{err.parameters}}` | `{{err.handling}}` |

Source: `Extracted.known_errors[]`.

## Section 7 — Failure handling (Table 6)

| Cell label | Token | Source |
|---|---|---|
| Accepted failure threshold | `{{accepted_failure_threshold}}` | `Extracted.accepted_failure_threshold` |
| Rerun on failure steps | `{{rerun_on_failure}}` | `Extracted.rerun_on_failure` (set by narrative pass — yes/no with reason) |

## Section 8 — Scheduling and triggers (Table 7)

| Cell label | Token | Source |
|---|---|---|
| Schedule / Frequency | `{{schedule_frequency}}` | `Extracted.schedule_frequency` |
| Expected bot utilization | `{{bot_utilization_pct}}` (followed by `%` in the cell) | `Extracted.bot_utilization_pct` |
| Triggers | `{{triggers}}` | `Extracted.triggers` |

## Section 9 — Reports (Table 8, repeating)

| Report Type | Update Frequency | Details | Monitoring Tool |
|---|---|---|---|
| `{{report.report_type}}` | `{{report.update_frequency}}` | `{{report.details}}` | `{{report.monitoring_tool}}` |

Source: `Extracted.reports[]`.

## Section 10 — Applications diagram (body paragraph)

Place a single paragraph containing `{{applications_diagram}}` directly under the "General Service and Application Architecture" heading. The filler clears the token text and inserts an inline image (the rendered PNG) into that paragraph.

## Section 11 — Step-by-step flow (body paragraph)

Place a single paragraph containing `{{steps}}` directly under the "AUTOMATION SBS FLOW:" line. The filler replaces it with one paragraph per step:

```
Step 1: <step.summary>
    App / Screen: <application> / <screen>
    Action: <action_detail>
    Inputs: <data_inputs joined>
    Outputs: <data_outputs joined>
    Decision rule: <decision_logic>
    Exception handling: <exception_paths joined>
```

Detail lines are omitted when the corresponding `Step` field is empty. `success_criterion` is no longer rendered (the step's logic above makes "done" obvious).

Source: `Extracted.steps[]`.
