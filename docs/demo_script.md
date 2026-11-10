# NovaTech demonstration — Round 2 (about 7 minutes)

The demo follows the **guided demo** stepper, so every screen opens at the right record and nothing depends on memory.
Every step below was run end to end in a real browser at projector size, 1366 × 768 (see `docs/testing.md`). The
percentages come from **deterministic logic**; with live Gemini the verdicts come from the model and may differ, and every
result shows which engine produced it.

**Before you present.**
1. Run `streamlit run app.py`, sign in as **Neha · Brand Manager** (password `novatech-demo`).
2. On the Overview, choose **Start from empty… → Empty and start**. The stepper appears with step 1 highlighted.
3. Keep the browser at 100 % zoom; close other tabs.

### 0 · The problem (30 s)
"Brands publish through many people, but their rules are scattered, vague and sometimes contradictory. Most checkers
assume the rules are right. BrandCanon investigates whether they hold — and shows the evidence for every verdict."

### 1 · Upload — Brand Constitution (60 s) · Neha
**Take me there** opens the upload dialog. Choose *Brand Guidelines*, *Product Specification* and *Marketing Presentation
2025* from `assets/sample_brand/` → **Extract knowledge**. Everything arrives *Pending review*.
**Approve pending** → authority 3 → **Approve all eligible**. The 2025 presentation (authority 1/5) stays pending.
Point at the source panel: every rule shows its passage and page. *The stepper ticks step 1.*

### 2 · Conflict — RuleProbe (40 s) · Neha
**Take me there** → Conflicts: "Battery life: 12 hours vs 15 hours", both sides with their authority. "BrandCanon never
picks a winner." Choose the specification, give a reason, **Resolve**.

### 3 · Test a rule — RuleProbe, the signature moment (90 s) · Neha
**Take me there** opens *"Maintain a friendly but professional tone."* → **Execute tests**.
Scroll to the **split view**: the gauge reads **40 %** against a 20 % limit; the outlined columns are the examples the
strict and lenient readings disagree on. Read the sentence aloud: *"The rule cannot decide cases #2, #4."*
Point at the coloured outcome dots and the **investigation map** below (click a node to open its record). "This is evidence for a person, not proof." → **Update rule after authorisation** → note "Agreed tone boundaries with the
brand team" → **Save version 2**.

### 4 · Audit — Content Auditor (90 s) · Priya
Press **Sign in as Priya for this step**, enter the password. **Take me there** fills in the post:
*"NovaTech guarantees 15 hours of battery life and will completely transform your productivity!"* → **Submit for audit**.
- **High · Contradicted** — "15 hours of battery life". **Examine finding**, then open **View source page**: page 3 of the specification with the
  12-hour line highlighted.
- **High · Unsupported** — "guarantees". **Medium · Unsupported** — "will completely transform your productivity".
**Accept all** → the **first draft → current revision** panel: 3 issues → 0, message preserved.
**Submit for approval**.

### 5 · Approve — Decision Memory (40 s) · Kavya
**Sign in as Kavya**, **Take me there**: the item is open. Write a rationale → **Approve**. It is stored with its rule,
source and version, and future "15 hours" claims will show *"An earlier review addressed a similar claim."*

### 6 · Insight — Governance Intelligence (30 s) · Neha
**Sign in as Neha**, **Take me there**. **Where to act**: fix the people, fix the rules, or fix the documents — here
the documents carry the largest share. Close: "We don't just catch mistakes — we show whether to fix the people, the rules
or the documents." **End guided demo**.

### Optional 30 s — Brand Knowledge Graph
Open **Knowledge Graph**: every document, rule, test, finding and decision, connected by stored relationships. Click the Product Specification node; its details panel lists the rules it contains and the findings it supports. "Every node is a real record — nothing here is decorative."

### If something goes wrong
- A step does not tick: the stepper only trusts stored records — finish the action (e.g. *Approve all eligible*, *Submit
  for approval*).
- No internet or Gemini quota: set `AI_PROVIDER=deterministic`; every result is labelled *Deterministic logic*.

### Likely questions
- **"How is RuleProbe different from asking an LLM?"** Controlled examples change one variable at a time; each is judged
  under two explicit readings (three passes each with Gemini); divergence is measured against a limit; reviewers mark
  outcomes; the rule is only changed by an authorised person, as a new version, and can be re-tested.
- **"What if the AI is wrong?"** Every finding cites a stored passage you can open on its page; people accept, edit,
  dismiss or override; nothing becomes official without a human. Failures are shown, never hidden.
- **"Is this real data?"** NovaTech is fictional and labelled illustrative; analytics are computed from records created
  through the real pipeline.
