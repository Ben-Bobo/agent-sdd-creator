# Email thread: expense report approvals

**From:** Mike O'Brien (Travel & Expense Lead, Operations)
**To:** Priya Patel (Automation Team)
**Date:** 2026-04-30
**Subject:** RE: Automating expense report manager approvals

---

**From:** Priya Patel
**Sent:** Apr 28, 2026 10:42 AM
**To:** Mike O'Brien
**Subject:** Automating expense report manager approvals

Mike, you mentioned at the steering committee that expense report approvals are
chewing up a lot of your team's time. Can you give me a quick rundown so I can
see if it's a candidate for automation? Specifically: what does the process
look like end to end, what apps are involved, how often does it run.

— Priya

---

**From:** Mike O'Brien
**Sent:** Apr 28, 2026 3:11 PM
**To:** Priya Patel
**Subject:** RE: Automating expense report manager approvals

Hi Priya — yes, glad you're looking at this.

We use **Concur** as the expense system. Employees file expense reports there
and submit them for manager approval. The issue is that ~40% of reports sit in
managers' queues for more than 5 business days, which hurts our reimbursement
SLA (we tell employees they'll be reimbursed within 10 business days, and that
slips constantly).

What my team (Jess and Tomas) does today:

1. Once a day, around 9am, one of them pulls a report out of Concur called
   "Pending Approval - Aged" which shows reports waiting more than 3 business
   days for manager sign-off. They export it to Excel.

2. They open the Excel, filter by manager, and for each manager group they
   compose an email reminding the manager which reports are waiting and how
   long they've been pending. Email goes via Outlook.

3. They mark in a tracking spreadsheet (just on a SharePoint site) that the
   nudge was sent, with the date.

4. If after 5 business days a report is still pending (so it's been waiting 8
   total), Jess escalates to the manager's manager — same kind of email but
   from her directly, not a reminder template. We can usually find the
   manager's manager in our HR system (Workday) but sometimes they just guess.

That's pretty much it. Volume is around 15-25 aged reports per day. It's a
high-priority process for us — we get heat from finance and HR when the SLA
slips.

One complication: if Jess or Tomas is out, nothing happens that day. That's
been an embarrassment a few times.

I haven't thought through edge cases like what if Concur is down, or what to do
if a manager has left the company. Those happen but rarely.

Let me know what info you'd need to scope this.

— Mike
