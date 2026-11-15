# BrandCanon: product roadmap and future development plan

This plan separates what is built (v2.2.0), what is partly built and what is not started. It lists no dates for work nobody has
begun, and no results nobody has measured.

## Where the product stands (v2.2.0)
Brand Constitution (upload, cited rules and facts, versions, approvals), RuleProbe (strict/lenient testing, conflicts, health
check), Content Auditor (text, visual and accessibility review), Decision Memory (reviews with reasons, precedents), Governance
Intelligence, Knowledge Graph, role-based screens, sign-up and sign-in (password, optional Google), stay-signed-in on refresh, and
an accuracy benchmark with 344 labelled items.

## Next (small, well understood)
| Item | Why | Notes |
|---|---|---|
| Measure Gemini on rule classification | The built-in ambiguity check catches few ambiguous rules on real guidelines (high precision, low recall). | Extend the benchmark compare from claims to rules. Needs a live key and a few minutes of API calls. |
| Human review of the 294 real-guideline labels | Labels came from one labeller. | Two reviewers, record disagreements, publish agreement. |
| Real user tests (3 to 5 people) | None have been run, so no usability results are reported. | Use the guided demo; time each step; note where people stop. |
| Real conflicts and claims in real guidelines | The benchmark has none, so conflict and claim accuracy are measured on NovaTech only. | Needs a brand that shares both a guideline and a product specification. |

## Later (needs design decisions)
- Storing visual-review results and campaign history (today they last for the session).
- Image-based and video checks beyond a single frame; logo detection against an uploaded logo file.
- Scheduled re-checks: re-run the health check when a guideline changes and tell the Brand Manager what moved.
- Multi-language rules and content (Hindi and other languages are accepted as text but not checked).
- Stronger authentication: single sign-on for companies, multi-factor, password recovery by e-mail.
- A hosted database (PostgreSQL) in place of per-visitor SQLite copies, so work survives restarts.
- Hand-off to publishing tools (CMS, design tools) after a person approves content.

## Deliberately not planned
Automated company discovery, web scraping of brand material, or any step that publishes or rejects content without a person. These
are outside the product's purpose.
