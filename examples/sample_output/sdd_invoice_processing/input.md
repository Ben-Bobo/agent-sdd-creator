# Kickoff: Vendor invoice processing automation

**Date:** 2026-04-22
**Attendees:**
- Priya Patel — Business Analyst (BA), Automation team
- Sarah Chen — Accounts Payable Lead, Finance
- Marcus Webb — Automation Manager

---

**Priya:** Thanks for making time, Sarah. Marcus mentioned you've been pushing to get the vendor invoice work automated — can you walk me through what the team actually does today?

**Sarah:** Yeah, so we get vendor invoices in a few different ways but the bulk — call it 80% — land in a shared Outlook mailbox called `ap-invoices@`. The rest come in via the supplier portal but let's park those for now, that's a different beast. The Outlook inbox gets maybe 70 to 90 a day. Mostly PDFs attached to plain emails from vendors.

**Priya:** OK. Volume of 70–90 a day in the Outlook inbox. What happens next?

**Sarah:** One of my team — Jamie or Rohan usually — opens each email, downloads the PDF, eyeballs it for vendor name, invoice number, amount, line items. Then they tab over to SAP — we're on ECC 6.0 — and go into transaction FB60 to post it.

**Priya:** FB60 in SAP ECC 6.0, got it. They key in the data manually?

**Sarah:** Manually. They look up the vendor in SAP by name — sometimes that's painful, the vendor master is messy and there are duplicates. If they can't find the vendor, they drop the invoice into a `vendor-not-found` subfolder in the inbox and email procurement to set up the vendor. That's the most common holdup honestly.

**Priya:** OK that's an exception path I'll capture. What else can go wrong?

**Sarah:** If the invoice amount is over five thousand dollars, it has to be approved by a manager before it gets posted. So the team enters it in SAP as "parked" status, then sends an email to the cost center owner — they get the owner's name from the PO if there's one attached, or they ask Jamie who he thinks owns it. Once the manager replies with approval, the team goes back into SAP and posts it.

**Priya:** Got it. Threshold is five thousand dollars, parked in SAP, owner approval needed via email. What about PDFs they just can't read — bad scans, foreign formats?

**Sarah:** Honestly we kick those back to the vendor. We don't try to fix them.

**Marcus:** Priya, on the AI side — there's a question of whether we run the PDFs through an extraction model first or stick with template-based reading. Worth flagging in the SDD.

**Priya:** Noted. Sarah, how often is the team posting? All day, batched, scheduled?

**Sarah:** Throughout the day. Nothing scheduled. They aim to clear the inbox by end of day but that often slips when volume's high.

**Priya:** And how critical is this — what happens if a day's worth doesn't get posted?

**Sarah:** Pretty bad. We have payment terms with most vendors and if invoices sit, the payment runs miss the cutoffs. We've had vendors threaten to put us on credit hold. So — I'd call it high. Not "the company stops" critical but definitely high.

**Priya:** OK, high business criticality. Last thing — what reporting do you need on this once it's running?

**Sarah:** A weekly summary email would be enough for me. How many were posted automatically, how many got kicked to my team, why. I don't need a dashboard, just an email.

**Priya:** Great. I think I have enough to draft something. I'll send a follow-up with anything else I need.

**Marcus:** Thanks Sarah.

**Sarah:** Thanks both.
