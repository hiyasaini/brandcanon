# BrandCanon — Brand Intelligence Workspace

> **Every brand has rules. We investigate whether they hold.**

BrandCanon is a brand-governance workspace for investigating brand inconsistencies. It is **manually managed and
document-based**: people upload PDF and DOCX documents, BrandCanon extracts and organises what they say, people validate
it, and only authorised knowledge is used to judge content. It does not fetch web pages, scrape sites or research
companies on its own.

1. **Brand Constitution** — the brand's source of truth: page-cited rules and facts, reviewed before they count.
2. **RuleProbe** — tests the rules themselves with controlled examples before they judge content.
3. **Content Auditor** — audits content against approved knowledge, with evidence for every finding.
4. **Decision Memory** — keeps authorised reviewer decisions and offers them as precedent.
5. **Governance Intelligence** — explains *why* problems recur (creator error, guideline defect, source conflict,
   knowledge gap).

Plus the **Brand Intelligence Overview** (with a **guided NovaTech demo**), the **Brand Knowledge Graph**, global search, **Settings** and **Help & documentation**. Flow: brand knowledge → rule testing → content auditing
→ human decisions → governance intelligence.

**Design.** A premium brand-intelligence workspace in two connected languages: a sage-green frame around a large white rounded workspace for the dashboards (Overview, Constitution, Content Intelligence, Decision Memory, Governance), and a dark investigation canvas for RuleProbe and the Brand Knowledge Graph. Manrope headings, Inter for the interface, JetBrains Mono for IDs and citations; tokens in `ui/styles.py`. Turquoise, lavender, coral, yellow and pink are reserved for entity types (rules, decisions, findings, test cases, documents), so the evidence trail and the graph use the same colours everywhere.

**The three improvements, visible in the product:** **RuleProbe** tests the guidelines themselves; the **Evidence Trail** links every finding to its rule, document, page and passage (and the **Brand Knowledge Graph** draws every stored relationship); **Decision Memory** retrieves earlier authorised decisions as precedent.

---

## Quick start (local, macOS / Linux)

Requires **Python 3.11 or newer** (3.12 recommended; the Gemini SDK needs 3.11+).

```bash
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                 # then edit .env (see "Live Gemini" below)
streamlit run app.py
```

Open <http://localhost:8501>. The **sign-in page** opens first. On first launch BrandCanon builds the fictional
**NovaTech (Demo)** workspace; every demo person signs in with the password `novatech-demo`
(Neha · Brand Manager, Kavya · Reviewer, Priya · Creator, …). To start your own brand, use **Create a workspace** on the
sign-in page.

**Windows (PowerShell):** `python -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, `pip install -r requirements.txt`,
`Copy-Item .env.example .env`, `streamlit run app.py`. Run the tests with `pytest`.

**Guided demo.** Sign in as Neha, then on the Overview choose **Start from empty…** (or **Start**). A stepper above every
screen walks through the Round 2 story — upload, conflict, rule investigation, audit, human decision, governance — says
which demo person does each step, signs you in as them with one click, and ticks each step only from what is stored.
Scope of this build against the Round 2 plan: `docs/round2_scope.md`.

## Share it as a link

To let judges open BrandCanon on any device from a link, see **docs/deploy.md**: a permanent Streamlit Community Cloud
link (about 10 minutes, once) or an instant quick tunnel from your Mac. Set `BRANDCANON_PUBLIC=1` so every visitor works
on a private copy of the demo.

## Live Gemini

BrandCanon uses Google's official **`google-genai`** SDK (not the deprecated `google-generativeai`). All calls go through
`services/gemini_service.py`.

1. Get a key from Google AI Studio.
2. In `.env`:
   ```
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your-key
   GEMINI_MODEL=gemini-3.5-flash-lite
   ```
3. Check connectivity (one short real request; the key is never printed):
   ```bash
   python scripts/check_gemini.py
   ```
   `OK — Gemini (…) answered in … ms` means it works. Otherwise it prints what failed: invalid key, quota, network,
   unavailable model or a malformed response. If the model is unavailable or keeps timing out for your key, run
   `python scripts/find_model.py`: it tries the models your key can use and saves the first one that answers.
   **Verified 10 Nov 2026** on the team's MacBook: `gemini-3.5-flash-lite` answered and `pytest -m live` passed 4/4.
4. Restart `streamlit run app.py`, then open **Settings → AI and privacy → Test Gemini connection**. The sidebar changes from
   *Gemini selected · not yet verified* to *Live Gemini · verified*.
5. Run the live smoke tests (they use a little quota): `bash scripts/run_live_tests.sh`.

**What Gemini does when enabled:**
- extracts and classifies rules, facts and terms, keeping only items whose text exists in the document;
- writes RuleProbe examples for undefined words such as "punchy", and gives strict and lenient verdicts (3 passes each);
- words clarified rules;
- runs a contextual tone, messaging and claim pass in the Content Auditor;
- suggests full rewrites, rejected if they introduce numbers not in the text or approved facts;
- summarises Decision Memory precedents (it may cite only the decisions it was given).

**Every result shows where it came from:**
- **Live Gemini · model**: a real response, validated against a schema. A reused cached response is marked *cached*.
- **Deterministic logic**: BrandCanon's own rules.
- **Demo fallback**: the pre-built demo workspace, which is always built without Gemini so it is reproducible.
- **Gemini failed: …**: Gemini was requested but failed. The deterministic checks ran instead, and a red message says what
  failed. Nothing is silently replaced with invented output.

**Keeping the key safe:**
- The key is read from `.env` (python-dotenv) or Streamlit secrets.
- It is never shown in the UI.
- It is scrubbed from every error message and log line.
- `.env` and `.streamlit/secrets.toml` are in `.gitignore`.
- A test fails if anything shaped like a Gemini key is committed.

## Tests

```bash
bash scripts/run_tests.sh        # mocked suite: no network, no quota → docs/test_results.txt
bash scripts/run_live_tests.sh   # live Gemini smoke tests → docs/live_test_results.txt (skipped if not configured)
```

## Deploy (Streamlit Community Cloud)

1. Push this folder to a GitHub repository. `.gitignore` keeps the database, `.env` and secrets out of git.
2. Create a new app on share.streamlit.io and set the entry point to `app.py`.
3. Under **Settings → Secrets** add `AI_PROVIDER = "gemini"`, `GEMINI_API_KEY = "…"` and `GEMINI_MODEL = "gemini-3.5-flash-lite"`.

The SQLite database on Community Cloud is temporary: it resets when the app restarts, which also resets accounts. BrandCanon
then rebuilds the demo workspace.

## Project structure

```
app.py                  navigation, sidebar identity, workspace switch
config.py               settings and domain vocabularies (authority levels, categories, statuses)
database/  schema.sql   relational schema v3 (about 20 tables, foreign keys, CHECK constraints, indexes, schema_version)
           db.py        connections, transactions, init/migrations, safe insert/update helpers
           repositories.py   all named, parameterised queries
services/  gemini_service.py      the only code that calls Gemini (google-genai; provider switch, errors, key scrubbing, cache)
           validation_service.py  Pydantic schemas for every model output
           file_service.py        type/size/signature checks, hashing, prompt-injection screening
           embedding_service.py   optional semantic re-ranking
modules/   document_parser.py, document_ingestion.py, knowledge_extraction.py, brand_constitution.py,
           ambiguity_detection.py, conflict_detection.py, rule_probe.py, evidence_retrieval.py,
           content_audit.py, approval_workflow.py, decision_memory.py, governance_analytics.py,
           visual_audit.py, report_generator.py, evaluation.py, demo.py, access.py, auth.py, notifications.py, queries.py,
           knowledge_graph.py (graph from stored records + layouts), search.py
ui/        styles.py (design tokens), components.py (header, cards, evidence trail, timeline…), login.py, help.py,
           tour.py (guided demo), graph.py (knowledge graph), search.py (global search)
           and one file per screen
tests/     96 mocked tests + 4 live Gemini smoke tests (tests/test_live_gemini.py, marker `live`)
docs/      architecture.md, testing.md, test_results.txt, limitations.md, user_guide.md, demo_script.md,
           round2_scope.md, screenshots/
assets/    logo, sample_brand/ (fictional NovaTech documents)
scripts/   make_sample_documents.py, run_tests.sh, run_live_tests.sh, check_gemini.py, find_model.py
```

## The five modules

| Module | What it does |
|---|---|
| **Brand Constitution** | Upload PDF or DOCX. Every sentence is stored as a passage with its page or section; candidate rules, numeric facts (with qualifiers) and terms are extracted and start as *Pending review*. Documents have their own review status, authority and versions (with version comparison). A three-area layout connects the document library, the extracted knowledge and a source/review panel that shows the exact passage — or says the reference is unavailable. Approve, edit (new version), reject, archive; destructive actions ask for confirmation. |
| **RuleProbe** | A three-panel investigation lab. Controlled examples change one characteristic at a time; reviewers can edit them or add their own. Each example is judged under a **strict** and a **lenient** reading, shown side by side with a divergence gauge (*Likely compliant*, *Potential violation*, *Uncertain*, *Needs human review*). Results are **potential findings** — *Ambiguous rule*, *Contradictory rules*, *Missing guidance*, *Model uncertainty* — until reviewed. Save, send for human review, approve the interpretation, or update the rule after authorisation (a new version). A test never changes a rule by itself. |
| **Content Intelligence** (Content Auditor) | Split screen: editor and marked-up text on the left, evidence-linked findings on the right. Terminology, product facts and qualifiers (against the highest-authority approved source), guarantees, superlatives and promises, tone, messaging, channel and accessibility rules, plus an optional Gemini pass. *Contradicted*, *Unsupported* and *Unverifiable* are kept distinct. Clickable finding cards: examine (highlights the phrase), the related rule, supporting passage and source page, a suggested-correction panel with accept, edit manually or dismiss with a reason; accept all, re-run, save the report, submit. Content can be pasted or loaded from a PDF or DOCX. |
| **Decision Memory** | Review queue, then decisions stored with rationale, rule, fact and source version. Searchable by phrase, product, rule, campaign, reviewer, status and date, with a detail panel (original vs corrected content, review history). Similar claims surface "An earlier review addressed a similar claim". Stale precedents are flagged; overrides keep history; decisions never become rules. |
| **Brand Knowledge Graph** | Documents, rules, test cases, findings, decisions and products as nodes; every edge a stored relationship. Search, entity and relationship filters, force-directed / circular / hierarchical / grid layouts, zoom and pan, legend, focus on a node; clicking a node shows its stored record and opens it in its own screen. Built with Plotly point selection — no extra dependency. |
| **Governance Intelligence** | Recurring violations, unresolved ambiguities, source conflicts, review turnaround; **Where to act** — fix the people, the rules or the documents; root causes and trends; most-violated rules, terminology issues, repeated unsupported claims, review trends; recommended actions, each tied to the records behind it. All computed from stored records; demo data is labelled illustrative. |

## AI and model disclosure

- **Gemini API** (`google-genai` ≥ 3.0, model set in `GEMINI_MODEL`): used only when `AI_PROVIDER=gemini`. When enabled, the
  relevant document or content text is sent to Google after emails and phone numbers are removed. Outputs are validated with
  Pydantic; invalid output is retried once, then rejected with a visible error.
- **Deterministic engine:** used for terminology, numbers and qualifiers, contrast, controlled test cases, retrieval (BM25
  weighted by document authority), root-cause tagging, and everything when Gemini is off.
- **Gemini embeddings** (optional, `BRANDCANON_EMBEDDINGS=1`): re-rank retrieved evidence.
- **Sign-in:** salted PBKDF2 password hashes in SQLite. This is prototype sign-in, not enterprise authentication.
- **Libraries:** Streamlit, Plotly, Pandas, PyMuPDF, python-docx, BeautifulSoup, Requests, Pillow, OpenCV, Pydantic,
  python-dotenv, google-genai, ReportLab (demo documents only), pytest.
- **AI coding assistance:** parts of this code were written with AI coding assistance during the build window. NovaTech, its
  products and its people are fictional.

See `docs/limitations.md` for what is not done yet.
