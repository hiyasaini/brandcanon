# Round 2 scope — what the plan promised and where it is

The Round 1 plan defined the **Round 2 MVP** as "runs end to end" across four modules, plus integration, deployment, first
metrics and 3–5 user tests. This page maps each promise to the screen that delivers it and the test that checks it.
Nothing from the Round 3 list was added for this round.

## Must-have features (Round 2)

| Module | Promised in Round 1 | Where in the app | Checked by |
|---|---|---|---|
| Constitution | PDF/DOCX upload | Brand Constitution → Upload documents | `test_ingestion.py`; browser scenario step 2 |
| | Rule and fact extraction with page citation | Extracted knowledge + source panel (*View source page*) | `test_ingestion.py`, `test_constitution.py`; step 4 |
| | Authority, scope, version | Library and rule detail; version comparison | `test_constitution.py`; step 3 |
| | Validate / edit / reject; term lists | Approve, edit (new version), reject, archive; Terminology tab | `test_constitution.py` |
| RuleProbe | Controlled cases | Test laboratory (editable, add your own) | `test_rule_probe.py` |
| | Strict / lenient evaluation | Split view: both readings per example + divergence gauge | `test_rule_probe.py`; guided-demo check 5 |
| | Ambiguity and conflict diagnosis | Investigation findings; Conflicts tab | `test_rule_probe.py`, `test_conflicts.py`; steps 5–6 |
| | Clarification, versioned rules | Update rule after authorisation → version 2 with diff | `test_rule_probe.py`; step 7 |
| Auditor | Text content; terminology; facts and qualifiers via retrieval | Content Auditor | `test_content_audit.py`; step 9 |
| | Claim support; tone and messaging | Contradicted / Unsupported / Unverifiable; tone findings | `test_content_audit.py` |
| | Highlights; rewrites | Marked-up text, *Examine finding*, Accept suggestion / Accept all, before → after panel | `test_content_audit.py`, `test_workflow.py`; step 10 |
| Review and memory | Roles and status flow | Sign-in per person; Draft → In review → Approved / Changes requested / Escalated / Rejected | `test_auth.py`, `test_workflow.py` |
| | Versions and diff; comments | Revision comparison; comments | `test_workflow.py`, `test_round2_ui.py` |
| | Approve / request changes with rationale | Decision Memory review queue (rationale required) | `test_decision_memory.py`; step 12 |
| | Precedents | "An earlier review addressed a similar claim" | `test_decision_memory.py` |
| Integrate | Analytics from stored records (plan item C) | Governance Intelligence, incl. *Where to act* | `test_workflow.py`; step 14 |
| | End-to-end run | Guided demo stepper (six steps, ticked from stored records) | `test_round2_ui.py`; guided-demo checks 1–14 |
| First metrics | Measured accuracy | Settings → Accuracy (labelled set of 50 items) | `docs/testing.md` |

## Plan items the team must still do themselves

- **3–5 user tests** and the **5–8 interviews and survey** promised in Round 1: not done by the build. Run them with the
  guided demo and report what you actually observe; do not report results that were not collected.
- **Deployment**: instructions are in the README (Streamlit Community Cloud with secrets). The build has not been deployed
  from here.
- **Live Gemini**: verified on 10 Nov 2026 on the team's MacBook — `check_gemini.py` OK with `gemini-3.5-flash-lite` and
  `pytest -m live` 4 passed (`docs/screenshots/09_live_gemini_verified.png`).

## Already present but outside the Round 2 demo

These existed before this round, still work and are tested, but are **not** part of the guided demo, so the Round 2 story
stays focused: basic image checks in the Content Auditor (Round 3 item "Visual & accessibility checks"), the *Missing
guidance* tab (Round 3 "Coverage gaps"), *Test all rules* (Round 3 "batch probing"), and the accuracy page (Round 3
"benchmark report"). Mention them only if asked.
