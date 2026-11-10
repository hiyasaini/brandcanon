# Architecture

```
┌──────────────────────────── ui/ (Streamlit) ────────────────────────────┐
│ login · dashboard (Overview) · constitution · ruleprobe · content_auditor │
│ decision_memory · governance · system (Settings) · help                   │
│ styles.py (design tokens) · components.py (evidence trail, cards, …)     │
└───────────────┬──────────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────── modules/ (business logic) ───────────────────┐
│ document_ingestion → document_parser → knowledge_extraction               │
│ brand_constitution (validation, versions, archive/delete)                 │
│ rule_probe ← ambiguity_detection + conflict_detection + evidence_retrieval│
│ content_audit → approval_workflow → decision_memory                       │
│ governance_analytics · notifications · visual_audit · report_generator    │
│ evaluation · demo                                                         │
│ access.py + auth.py (sign-in; role checks in code)                 │
└───────────────┬───────────────────────────────┬──────────────────────────┘
                ▼                               ▼
     database/ (SQLite)                services/
     schema.sql · db.py ·              gemini_service · validation_service ·
     repositories.py                   file_service · embedding_service
```

## Key decisions

| Decision | Why |
|---|---|
| **Streamlit with custom CSS** | One language (Python) for a two-person team. The design system lives in `ui/styles.py` and `.streamlit/config.toml`: the brief's palette (sage #52665C, light sage #E6EBE5, forest #263A32, green #718A7B, mint #B9CDBD, text #242824, secondary #858D86, borders #E6E9E5, dark workspace #101114 / panel #191B22, entity colours turquoise #56C9C1, lavender #AD83EE, coral #F17D83, yellow #F0CF72, pink #E79BD0) with Manrope / Inter / JetBrains Mono. Secondary text #858D86 is 3.4:1 on white, so small text uses a darker shade of the same hue (#646C65, 5.4:1); primary buttons use forest (white text 11:1). `styles.dark()` switches a page to the dark investigation design. Navigation: a top bar (logo, workspace, global search, notifications, profile) and a collapsible sidebar of page links (`st.navigation(position="hidden")`); cross-screen links set a one-shot session value the destination reads, and tabs are stateful. |
| **Knowledge graph from stored records** | `modules/knowledge_graph.py` builds nodes and edges only from foreign keys and stored lists (rule → document version, test → cases, findings → rule / passage / decision, decisions → rule). Layouts (force-directed with a fixed seed, circular, hierarchical, grid) are plain Python. The UI draws it with Plotly and reads clicks through `st.plotly_chart(on_select="rerun")`, so no new dependency is needed; the selection is remembered across filter and layout changes. |
| **Evidence trail as the identity** | `components.evidence_trail` draws content → rule → source document and page → passage → decision identically on every screen; a missing link is shown as missing, never filled in. |
| **Potential findings, human decisions** | RuleProbe records a potential finding and an investigation state (draft → saved → sent for human review → interpretation approved / rule updated). Only an authorised Brand Manager changes a rule, as a new version. |
| **SQLite with a relational schema** | Zero setup, file-based and transactional, with foreign keys, CHECK constraints and indexes. JSON is used only for parsed rule constraints and a short list of related rule ids. `schema_version` supports migrations. |
| **Passages as the unit of evidence** | Every extracted sentence is stored with its page or section. Rules, facts and findings point to `passage_id`, so a citation always refers to stored text and never to text the model generated. |
| **Hybrid engine** | Exact checks (terms, numbers and qualifiers, contrast, scope) are code, so they are reproducible. Gemini (selected with `AI_PROVIDER=gemini`) adds judgement only where interpretation is needed. Its output must match a schema, quote text that exists and pass grounding checks (numbers, cited ids) before it is used or cached. |
| **No silent fallback** | `gemini_service.generate` either returns validated data or raises `GeminiError` with a kind and a safe message. Callers that can still produce a useful result do so with deterministic logic, but store the label "Deterministic logic — Gemini failed: …", and the UI shows the error. Each stored result says whether it came from live Gemini, a cached Gemini response, deterministic logic or the demo fallback. |
| **RuleProbe = controlled cases × two readings** | One-variable-at-a-time examples make a verdict flip attributable to a single characteristic. The *strict vs lenient* divergence measures interpretive room. Self-inconsistency across repeated model passes is reported separately as *model uncertainty*. Clarifying a rule turns vague words into measurable constraints, so divergence drops measurably. |
| **Authority and versions** | Documents carry an authority rank (0–5) and versions. A new upload of the same document archives its old rules and supersedes its old facts. Conflicts are recorded, never silently resolved. |
| **Decision Memory as precedent, not policy** | Decisions store the claim, rule, fact, source version, product and channel. Retrieval weighs similarity and context, flags precedents tied to non-current source versions, and skips superseded decisions. |
| **Root causes on first drafts** | Governance counts the issues in revision 1, so later fixes do not hide where problems started. |

## Data model (main tables)

```
workspaces 1─* users (password_hash)
workspaces 1─* documents (review_status) 1─* document_versions 1─* passages
document_versions 1─* brand_rules (passage_id) 1─* rule_revisions
document_versions 1─* brand_facts (passage_id)
brand_rules 1─* rule_tests (investigation_state, notes) 1─* rule_test_cases
source_conflicts 1─* conflict_sides ─→ brand_rules | brand_facts
content_submissions 1─* content_revisions 1─* audit_reports 1─* audit_findings ─→ rule | fact | passage
decisions ─→ submission, revision, finding, rule, fact, document_version (source version), supersedes_decision_id
approvals ─→ submission, revision, reviewer, decision
comments, activity_log, llm_cache, terms, schema_version
```

## Security and responsible AI

- **API key:** read from `.env` (python-dotenv) or Streamlit secrets only. It is never shown in the UI, it is removed from error
  messages and log lines by `gemini_service.scrub`, and raw SDK tracebacks are not chained into user-facing errors. A test
  fails if a key-shaped string is committed.
- **Sign-in:** a separate page shown before the app; every URL leads there until someone signs in. Passwords are salted
  PBKDF2-SHA256 hashes (200,000 iterations) compared in constant time, and failure messages do not reveal which part was
  wrong.
- **Uploads:** extension allow-list, size limit, PDF and DOCX signature check, SHA-256 hash.
- **Prompt injection:** uploaded and submitted text is wrapped in `<untrusted>` tags under a system instruction to treat it as data. Instruction-like phrases are detected and flagged on the document.
- **Personal data:** emails and phone numbers are redacted before any text is sent to Gemini.
- **Roles:** checked in `modules/access.py`. Only Brand Managers upload, approve or edit rules and resolve conflicts. Only Reviewers and Brand Managers decide content, and escalated items need a Brand Manager.
- **Destructive actions:** archiving and deleting ask for confirmation, and deleting also removes the conflicts that referenced the document.
- **Human control:** BrandCanon never publishes or rejects content on its own.
