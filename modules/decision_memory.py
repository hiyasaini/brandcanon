"""Decision Memory: authorised reviewer decisions, retrieved as context-aware precedent.

Safeguards:
* A precedent is advice for the reviewer — it never changes rules or decides content automatically.
* Retrieval weighs claim similarity AND context (product, channel, rule, fact).
* Decisions based on a source version that is no longer current are flagged and down-weighted.
* Decisions that a later decision superseded are not offered as precedent.
"""
import re

from database import db, repositories as repo
from modules.access import require
from services import gemini_service, validation_service as vs

VERB = {"Finding upheld": "was flagged and corrected", "Finding overridden": "was allowed by a reviewer",
        "Approved": "was approved", "Changes requested": "was sent back for changes", "Rejected": "was rejected",
        "Escalated": "was escalated"}


def _tokens(t):
    return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 2}


def similarity(a, b):
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def active_decisions(ws):
    rows = repo.list_decisions(ws)
    superseded = {r["supersedes_decision_id"] for r in rows if r["supersedes_decision_id"]}
    return [r for r in rows if r["id"] not in superseded]


def precedents_for(ws, finding, product=None, channel=None, k=2, exclude_submission=None):
    """Most relevant earlier decisions for one finding."""
    if finding.get("classification") == "Verified":
        return []
    out = []
    for d in active_decisions(ws):
        if d["decision"] not in ("Finding upheld", "Finding overridden") or d["submission_id"] == exclude_submission:
            continue
        sim = similarity(finding.get("quote") or finding.get("message"), d["claim_text"])
        same_fact = finding.get("fact_id") and finding.get("fact_id") == d["fact_id"]
        same_rule = finding.get("rule_id") and finding.get("rule_id") == d["rule_id"]
        if sim < 0.25 and not same_fact and not same_rule:
            continue
        if finding.get("category") and d["finding_category"] and finding["category"] != d["finding_category"]:
            continue
        score = sim + 0.6 * bool(same_fact) + 0.4 * bool(same_rule) + 0.3 * (d["product"] == product) + 0.15 * (d["channel"] == channel)
        stale = d["source_current"] == 0
        if stale:
            score *= 0.5
        out.append((score, d, stale))
    out.sort(key=lambda x: -x[0])
    res = []
    for score, d, stale in out[:k]:
        why = (f"A similar claim (“{d['claim_text'][:80]}”) {VERB.get(d['decision'], d['decision'].lower())} on {d['created_at'][:10]}"
               f" by {d['reviewer_name']}: {d['explanation']}")
        if stale:
            why += f" Note: that decision relied on {d['source_title']} v{d['source_version']}, which is no longer the current version."
        res.append({**d, "score": round(score, 2), "stale": stale, "summary": why})
    return res


def attach(ws, findings, product=None, channel=None, exclude_submission=None):
    for f in findings:
        f["precedents"] = precedents_for(ws, f, product, channel, exclude_submission=exclude_submission)
    return findings


def override(ws, reviewer_id, decision_id, explanation):
    """Replace an earlier decision with a new one; the old one stays in history but stops being precedent."""
    require(reviewer_id, "Reviewer", "Brand Manager")
    if not (explanation or "").strip():
        raise ValueError("An explanation is required to override a decision.")
    old = db.get("decisions", decision_id)
    new_decision = "Finding overridden" if old["decision"] == "Finding upheld" else "Finding upheld"
    nid = db.insert("decisions", workspace_id=ws, submission_id=old["submission_id"], revision_id=old["revision_id"],
                    finding_id=old["finding_id"], rule_id=old["rule_id"], fact_id=old["fact_id"],
                    source_version_id=old["source_version_id"], decision=new_decision, claim_text=old["claim_text"],
                    finding_category=old["finding_category"], explanation=explanation.strip(), channel=old["channel"],
                    product=old["product"], campaign=old["campaign"], reviewer_id=reviewer_id,
                    supersedes_decision_id=decision_id, created_at=db.now())
    repo.log(ws, reviewer_id, "Overrode earlier decision", "decision", nid, explanation[:100])
    return nid


def summarise_precedents(finding, precedents):
    """Gemini summary of what earlier decisions suggest for this finding. Advice only; it decides nothing.

    Raises GeminiError if Gemini is off or fails, or if the summary cites decisions it was not given.
    """
    if not precedents:
        raise ValueError("There are no precedents to summarise.")
    if not gemini_service.enabled():
        raise gemini_service.not_available_error()
    ids = {p["id"] for p in precedents}
    block = "\n".join(
        f"[{p['id']}] {p['created_at'][:10]} · {p['decision']} by {p['reviewer_name']} · claim “{p['claim_text']}” · "
        f"channel {p['channel'] or '—'} · product {p['product'] or '—'} · rationale: {p['explanation']}"
        + (" · NOTE: based on a source version that is no longer current" if p.get("stale") else "")
        for p in precedents)
    def grounded(obj):
        if not set(obj.decision_ids) <= ids:
            raise gemini_service.GeminiError("ungrounded", "Gemini's summary cited decisions that were not provided. "
                                                           "It was discarded.")
    with gemini_service.tracking() as sources:
        res = gemini_service.generate(
            "A reviewer is looking at this FINDING. Using ONLY the EARLIER DECISIONS listed, summarise in 2–3 sentences what "
            "they suggest, and say if any rely on outdated sources. Do not decide for the reviewer and do not invent decisions. "
            'Return JSON {"summary": str, "decision_ids": [ids of the decisions you used]}\n'
            "FINDING:\n" + gemini_service.untrusted(f"{finding.get('quote') or ''} — {finding.get('message') or ''}") +
            "\nEARLIER DECISIONS:\n" + gemini_service.untrusted(block), vs.PrecedentSummary, temperature=0.2, check=grounded)
    return {"summary": res.summary, "decision_ids": res.decision_ids, "engine": gemini_service.label_for(sources)}
