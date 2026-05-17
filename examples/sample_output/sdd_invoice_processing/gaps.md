# Open questions for the business — Vendor Invoice Processing Automation

These details are missing or only partially covered in the source material. Forward to the relevant stakeholder before development starts.

_Overall coverage: 70%_

## Per-step gaps

### step_1 — Read unread emails from shared mailbox ap-invoices@
- **decision_logic (missing):** In step 1, when reading unread emails, should the bot process every unread email in the inbox or only emails that have at least one attachment? And should it skip emails that are already in subfolders like 'vendor-not-found'?
- **exception_paths (missing):** In step 1, if the call to retrieve unread emails fails (e.g., a connectivity issue), what should the bot do — retry immediately, wait and retry after a delay, or alert someone?
- **success_criterion (partial):** For step 1, is 'unread emails retrieved successfully' satisfied even when there are zero unread emails (i.e., an empty inbox is a normal success), or should the bot take some action when the inbox is empty?

### step_2 — Download PDF attachment from email
- **decision_logic (partial):** In step 2, when an email has no PDF attachment, the description says 'flag for manual review or ignore — clarification needed.' What should actually happen: should the email be ignored (left unread), moved to a specific folder, or should someone on the AP team be notified?
- **exception_paths (partial):** In step 2, if the PDF download fails (e.g., the attachment is corrupted or the download times out), what should the bot do — retry, skip that invoice, or alert someone?

### step_3 — Extract invoice fields from PDF
- **application_screen (missing):** In step 3, which tool or service performs the PDF field extraction — is this a specific application, an internal system, or a third-party service you currently use?
- **action (missing):** In step 3, how does the extraction actually work today when you process an invoice manually — do you open the PDF and type fields into a form, or is there already some tool that reads it? This will help determine whether to use template-based or AI-based extraction for the automation.
- **decision_logic (partial):** In step 3, the confidence threshold that determines whether a PDF is 'unreadable' is listed as TBD. What would make you consider an extraction result good enough to proceed — for example, is it acceptable if the vendor name and total amount are found even if line items are missing, or do all fields need to be present?
- **success_criterion (partial):** For step 3, which fields are strictly required for processing to continue — is PO number optional, and are line items required or just nice-to-have?

### step_4 — Return unreadable PDF to vendor
- **decision_logic (missing):** In step 4, what text goes in the email body sent back to the vendor — is there a standard template you use today, or do you write it fresh each time? Please share the typical wording.
- **exception_paths (missing):** In step 4, if the reply email to the vendor fails to send, what should happen — should the bot retry, log the failure, or alert the AP team?

### step_5 — Look up vendor in SAP ECC vendor master
- **application_screen (partial):** In step 5, which SAP transaction or screen do you use to look up a vendor by name — for example, do you use XK03, FK03, or a vendor master search transaction? What menu path or transaction code do you enter?
- **action (missing):** In step 5, when you look up a vendor in SAP by name, what is the exact sequence of steps — which transaction code do you enter, which fields do you search by (exact name, partial name, wildcard?), and which field gives you the SAP Vendor ID to carry forward?
- **decision_logic (partial):** In step 5, when would a vendor match be considered 'ambiguous' — for example, if there are two vendors with very similar names, how many results in the list would trigger the ambiguous path vs. a clear single match?

### step_6 — Handle vendor-not-found exception
- **data_inputs (partial):** In step 6, what is the procurement team's email address that the notification is sent to — is it a single shared inbox, a distribution list, or does it vary?
- **decision_logic (missing):** In step 6, what text goes in the procurement notification email — is there a standard message template you use today, or do you write it each time? Please share the typical wording.
- **exception_paths (missing):** In step 6, if moving the email to the 'vendor-not-found' subfolder or sending the procurement notification fails, what should the bot do — retry, log the error, or alert the AP team?

### step_7 — Determine approval requirement based on invoice amount
- **application_screen (missing):** Step 7 is a routing decision based on invoice amount — does the bot make this decision internally using the extracted amount, or does it involve opening any system or screen to check the amount?
- **exception_paths (missing):** In step 7, what should happen if the invoice amount could not be extracted (i.e., it is blank or unreadable) — should the bot treat it as over $5,000 and park it for approval, or flag it as an exception for the AP team?

### step_8 — Enter invoice in SAP FB60 as parked
- **action (missing):** In step 8, when you park an invoice in SAP FB60, what is the exact sequence of steps — which fields do you fill in and in what order (e.g., vendor ID, invoice date, amount, line items, cost center), and which specific button or menu option saves it as 'parked' rather than fully posted?
- **decision_logic (missing):** In step 8, are there any additional SAP fields beyond vendor ID, invoice number, amount, line items, and PO number that you fill in when parking an invoice — for example, invoice date, payment terms, company code, or G/L account?
- **exception_paths (missing):** In step 8, if SAP returns an error when trying to park the invoice (e.g., a validation error or missing required field), what should the bot do — flag it for the AP team to handle manually, retry, or something else?

### step_9 — Send approval request email to cost center owner
- **data_inputs (partial):** In step 9, when the invoice has no PO attached, how do you currently find the cost center owner — is there a lookup table, an SAP field on the parked document, or do you ask someone?
- **decision_logic (partial):** In step 9, after sending the approval request, what happens if the cost center owner replies with a rejection (not an approval) — what should the bot do with the parked invoice and how should the AP team be informed?
- **exception_paths (partial):** In step 9, if no approval reply arrives after a certain number of days, is there a deadline or escalation — for example, do you chase the approver after 2 days, and who do you escalate to if they still don't respond?

### step_10 — Post invoice in SAP FB60
- **action (missing):** In step 10, when posting an invoice in SAP FB60, what is the exact sequence of steps — and specifically, when coming from the approval flow (posting a previously parked document), do you search for the parked document number to reopen it, or do you enter it fresh? Which button or menu option finalises the post?
- **decision_logic (missing):** In step 10, are there any SAP validation rules or posting blocks that could prevent an invoice from posting — for example, a PO quantity mismatch or a blocked vendor — and if so, what should the bot do when that happens?
- **exception_paths (missing):** In step 10, if SAP returns a posting error, what should the bot do — move the invoice to a manual queue, notify the AP team, or retry?

### step_11 — Mark source email as read / processed
- **decision_logic (missing):** In step 11, should the bot also move successfully processed emails to a specific 'processed' or 'completed' subfolder, or is marking them as read sufficient to consider them done?
- **exception_paths (missing):** In step 11, if marking the email as read fails, should the bot retry or simply log the failure and continue — would leaving it unread cause the bot to accidentally reprocess the same invoice next time?

### step_12 — Send weekly summary email to AP Lead
- **trigger (partial):** In step 12, what day of the week and time should the weekly summary email be sent — for example, every Monday morning, or every Friday end of day?
- **data_inputs (partial):** In step 12, where does the bot get the weekly processing statistics from — does it need to query a log or database it maintains throughout the week, or is there another source?
- **decision_logic (missing):** In step 12, should the weekly summary email be sent even if no invoices were processed that week, or only if there is activity to report?
- **exception_paths (missing):** In step 12, if the weekly summary email fails to send, should the bot retry and if so how many times, or simply log the failure?

## Overall

- **sla_timing (partial):** The goal is to clear the inbox by end of business each day — is there a specific cut-off time (e.g., 5:00 PM local time) that counts as 'end of business', and does this apply on weekends or only weekdays?
- **access_authentication (missing):** For SAP ECC, how does the bot log in — does it use a dedicated service account with a username and password, and is there any SAP-side approval needed to allow automated FB60 postings under that account?
- **compliance_audit (missing):** Are there any audit or compliance requirements for this invoice process — for example, do you need to keep a log of every invoice processed (with amounts, vendor IDs, and posted document numbers), and if so how long must those records be retained?
- **reporting (partial):** Beyond the weekly summary email to Sarah Chen, does anyone else need visibility into the bot's activity — for example, should the AP team be able to see a real-time dashboard, or are there any other reports required by finance or management?
