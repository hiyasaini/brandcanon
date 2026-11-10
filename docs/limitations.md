# Known limitations (honest status)

## Live Gemini — verified on 10 Nov 2026
- **A real request succeeded.** On the team's MacBook (macOS, Python 3.14.10) with a real Google AI Studio key:
  `python scripts/check_gemini.py` → *"OK — Gemini (gemini-3.5-flash-lite) answered in 1622 ms"*, and
  `pytest -m live` → **4 passed** (`tests/test_live_gemini.py`). Evidence: `docs/screenshots/09_live_gemini_verified.png`.
- `gemini-2.5-flash` is no longer available to new keys (HTTP 404) and `gemini-3.8-flash` repeatedly timed out (HTTP 504) for
  this key, so the default model is now `gemini-3.5-flash-lite`. `python scripts/find_model.py` lists the models a key can
  use, tries the fastest first and saves the first one that answers into `.env`.
- These runs happened on the team's machine, not in the build environment (whose network blocks the Gemini API); the
  result above is taken from the team's terminal output.
- **Prompt quality with the live model is untested.** Prompts were written against the documented JSON behaviour. The real
  model may return fewer usable items, for example extracted rules that do not match the document text exactly and so get
  dropped. RuleProbe numbers will differ from the deterministic demo values (such as 40% divergence for R002).
- **Model names:** model availability changes. If `gemini-3.5-flash-lite` or the embedding model is unavailable to your key, set
  `GEMINI_MODEL` / `GEMINI_EMBED_MODEL`; the app reports an unavailable model clearly.
- **Cost and quota:** a RuleProbe run makes 6 calls (3 passes × 2 readings), plus 1 to generate examples and 1 for
  clarification wording. Extraction makes 1 call per page. Responses are cached by prompt, and reused responses are labelled
  *cached*.

## Deterministic engine limits
- **RuleProbe vocabulary:** RuleProbe can only build controlled tests for characteristics it knows: formality, informality and slang, emoji, excitement, sales pressure, superlatives and sentence length. Vague words outside its lexicon, such as "punchy" or "authentic", are reported as possible uncertainty rather than tested. On the labelled set this gives an ambiguity-detection recall of 0.80.
- **Conflict detection:**
  - It only finds rules that pull in opposite directions on a known characteristic, or facts with different values for the same product attribute.
  - It misses conflicts that need world knowledge, such as "concise" vs "explain every feature". Recall on the labelled set is 0.67.
  - It can flag tensions that a person would accept, for example "bold and exciting" vs "at most one exclamation mark".
- **Document-based only (by design):** there is no web import, scraping or automated company research; uploads are PDF
  and DOCX. Tables inside PDFs, unusual layouts and scanned documents may be missed (no OCR).
- **Rule extraction:** extraction relies on sentence patterns (directives, `Attribute: value` lines, quoted terms). Unusual layouts, tables in PDFs and scanned documents can be missed. A scanned PDF has no text layer, so it is reported as empty; there is no OCR.
- **Divergence is evidence, not proof:** a high divergence means the rule is open to interpretation; a person decides whether that matters.

## Product scope
- **Embedding failures:** when the optional embeddings are on and fail, evidence ranking falls back to BM25. The failure is
  recorded in Settings → AI and privacy, but it is not repeated on each audit.
- **Visual checks:** dimensions, colours, contrast, alt text and OpenCV logo template matching are basic and explainable, not visual AI. Their results are shown but not stored in the audit report.
- **Prototype sign-in only:**
  - Passwords are salted PBKDF2 hashes, and roles are enforced in code.
  - There is no single sign-on, multi-factor authentication, password recovery or server-side session store.
  - Refreshing the browser tab signs you out (sessions live in the server's memory for that tab); links between
    screens keep you signed in.
  - Lockout after repeated failures is per browser session only.
  - Accounts created before sign-in existed can set their first password on the sign-in page. This is a convenience for
    migration, not a secure activation flow.
  - Demo accounts share a published password.
- **Single-instance storage:** SQLite on one machine. On Streamlit Community Cloud the database is temporary.
- **Evaluation set:** the labelled set is small (50 items), was written by the team, and is for a fictional brand. It is an early signal; see Settings → Accuracy.
- **Not verified:** no enterprise security or compliance certification is claimed.

## Interface
- **Optimised for desktop and laptop.** RuleProbe and the Content Auditor use multi-panel layouts; on tablets and phones
  Streamlit stacks the panels and collapses the sidebar, which works but is less comfortable.
- **Rows inside data grids** (extracted knowledge, product facts) are selected with the row checkbox; the grid itself is
  drawn on a canvas, so screen readers get less detail there than in the rest of the interface.
- **Fonts** load from Google Fonts; offline, the interface falls back to Georgia/Helvetica/Menlo.
- **Turnaround** is measured from the revision a reviewer decided on to the decision, because submission-time stamps of
  the backdated demo history are not reliable.

## Public link
- With `BRANDCANON_PUBLIC=1` every visitor works on a private copy of the demo kept in the server's temporary folder.
  A copy lasts for that browser tab (reloads included); copies unused for a day are deleted. On Streamlit Community
  Cloud a restart of the app clears all copies.
- Every visitor's Gemini requests use the deployer's API key and its quota. If the quota runs out, results say so and
  the deterministic checks still run.
- Free Streamlit Community Cloud apps sleep after a period without visitors; the first visit after that takes about a
  minute to wake.
