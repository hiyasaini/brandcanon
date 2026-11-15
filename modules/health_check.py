"""Whole-guideline health check: every rule tested in one run and the results ranked into one prioritised fix list.

Nothing here is invented. Each row comes from a stored RuleProbe test (ambiguity, with the clarified wording RuleProbe or
Gemini proposed), a stored open conflict, or a context with no rule at all. The priority score is a plain, visible sum:

    open conflict touching the rule ........ 40
    ambiguous rule ......................... 30 + up to 20 for how often strict and lenient readings disagree
    model uncertainty ...................... 15
    audited content cited the rule ......... 3 per finding, at most 15   (the rule is actually hit by real content)
    context with no specific rule .......... 20

A higher score means "fix this sooner". It ranks the work; it does not say a rule is wrong.
"""
import json
from datetime import datetime

from database import db, repositories as repo
from modules import conflict_detection, rule_probe

LIVE = ("Approved", "Pending Validation", "Needs Clarification")
POINTS = {"conflict": 40, "ambiguous": 30, "uncertain": 15, "gap": 20, "per_finding": 3, "finding_cap": 15, "divergence_max": 20}
FORMULA = ("open conflict 40 · ambiguous rule 30 + up to 20 for divergence · model uncertainty 15 · "
           "3 per audit finding that cites the rule (max 15) · context with no rule 20")


def run(ws, user_id, context="All content"):
    """Test every testable rule and detect conflicts (Brand Manager only), then return the ranked result."""
    n_tested, n_conf = rule_probe.scan(ws, user_id, context)
    out = build(ws)
    out["ran"] = {"tested": n_tested, "new_conflicts": n_conf}
    return out


def _usage(ws):
    rows = db.fetch_all("""SELECT f.rule_id, COUNT(*) n FROM audit_findings f
                           JOIN audit_reports r ON r.id = f.report_id
                           WHERE r.workspace_id = ? AND f.rule_id IS NOT NULL AND f.classification != 'Verified'
                           GROUP BY f.rule_id""", (ws,))
    return {r["rule_id"]: r["n"] for r in rows}


def build(ws):
    """Rank what is stored right now. Reads only; it never runs a test."""
    rules = repo.list_rules(ws, LIVE)
    usage = _usage(ws)
    rows, tested, clear = [], 0, 0
    untested = []
    for r in rules:
        t = repo.latest_test(r["id"])
        conflicts = repo.open_conflicts_for_rule(r["id"])
        issues, score, why = [], 0, []
        rewording, engine, test_id = "", "", None
        if t:
            tested += 1
            test_id, engine = t["id"], t["engine"]
            if t["classification"] == "Clear rule":
                clear += 1
            elif t["classification"] == "Ambiguous rule":
                issues.append("Ambiguous rule")
                score += POINTS["ambiguous"] + round(min(1.0, t["divergence"]) * POINTS["divergence_max"])
                why.append(f"strict and lenient readings disagree on {t['divergence']:.0%} of controlled examples")
                rewording = t["recommendation"] or ""
            elif t["classification"] == "Model uncertainty":
                issues.append("Model uncertainty")
                score += POINTS["uncertain"]
                why.append(t["issue"])
                rewording = t["recommendation"] or ""
        elif rule_probe.amb.rule_dims(r) or (rule_probe.amb.vague_terms(r["text"]) and r["category"] in rule_probe.amb.TESTABLE_CATEGORIES):
            untested.append(r["code"])
        if conflicts:
            issues.append("Open conflict")
            score += POINTS["conflict"]
            why.append("; ".join(c["title"] for c in conflicts))
            rewording = rewording or "Resolve it in RuleProbe → Conflicts: narrow a scope, archive one rule, or confirm both can coexist."
        n_use = usage.get(r["id"], 0)
        if issues and n_use:
            score += min(POINTS["finding_cap"], POINTS["per_finding"] * n_use)
            why.append(f"cited by {n_use} audit finding{'s' if n_use != 1 else ''}")
        if issues:
            rows.append({"kind": "rule", "rule_id": r["id"], "code": r["code"], "text": r["text"], "category": r["category"],
                         "issues": issues, "score": score, "why": why, "rewording": rewording, "engine": engine, "test_id": test_id})
    gaps = conflict_detection.coverage_gaps(ws)
    for g in gaps:
        rows.append({"kind": "gap", "rule_id": None, "code": "—", "text": f"No rule is specifically scoped to {g}.", "category": "Missing guidance",
                     "issues": ["Missing guidance"], "score": POINTS["gap"], "why": [f"creators working on {g} only have general rules"],
                     "rewording": "Add guidance for this context to a source document and upload it, or confirm that general rules are enough. "
                                  "BrandCanon does not write an official rule.",
                     "engine": "", "test_id": None})
    rows.sort(key=lambda x: (-x["score"], x["code"]))
    for i, x in enumerate(rows, 1):
        x["rank"] = i
    return {"rows": rows, "gaps": gaps, "untested": untested, "n_rules": len(rules), "n_tested": tested, "n_clear": clear,
            "n_ambiguous": sum(1 for x in rows if "Ambiguous rule" in x["issues"]),
            "n_conflicts": len(repo.list_conflicts(ws, "open")),
            "generated_at": datetime.now().isoformat(timespec="seconds")}


def markdown(ws_name, h):
    L = [f"# BrandCanon guideline health report — {ws_name}", "",
         f"Generated {h['generated_at'].replace('T', ' ')} from stored RuleProbe tests, conflicts and coverage. "
         "Scores rank the work; they do not say a rule is wrong. People decide every change.", "",
         f"- Rules in scope: {h['n_rules']} · tested: {h['n_tested']} · clear: {h['n_clear']}",
         f"- Ambiguous rules: {h['n_ambiguous']} · open conflicts: {h['n_conflicts']} · contexts with no rule: {len(h['gaps'])}"]
    if h["untested"]:
        L.append(f"- Testable but not yet tested: {', '.join(h['untested'])}")
    L += ["", f"Priority score: {FORMULA}.", "", "## Prioritised fix list", ""]
    if not h["rows"]:
        L.append("No ambiguity, conflict or coverage issue is recorded. Run the health check to refresh it.")
    for x in h["rows"]:
        L += [f"### {x['rank']}. {x['code']} · {', '.join(x['issues'])} · score {x['score']}", "", f"> {x['text']}", "",
              "- Why: " + "; ".join(x["why"])]
        if x["rewording"]:
            L.append(("- Proposed wording: " if "Ambiguous rule" in x["issues"] else "- Suggested next step: ") + x["rewording"]
                     + (f"  _(engine: {x['engine']})_" if x["engine"] and "Ambiguous rule" in x["issues"] else ""))
        L.append("")
    L.append("_Proposed wordings are suggestions for a Brand Manager to accept or change in RuleProbe._")
    return "\n".join(L)


def html(ws_name, h):
    """A printable page (Print → Save as PDF)."""
    from html import escape as e
    cards = "".join(
        f"<div class='c'><div class='h'><b>{x['rank']}. {e(x['code'])}</b> <span>{e(', '.join(x['issues']))}</span><i>score {x['score']}</i></div>"
        f"<p class='q'>{e(x['text'])}</p><p><b>Why:</b> {e('; '.join(x['why']))}</p>"
        + (f"<p><b>{'Proposed wording' if 'Ambiguous rule' in x['issues'] else 'Next step'}:</b> {e(x['rewording'])}</p>" if x["rewording"] else "")
        + "</div>" for x in h["rows"]) or "<p>No ambiguity, conflict or coverage issue is recorded.</p>"
    return (f"<!doctype html><meta charset='utf-8'><title>Guideline health report — {e(ws_name)}</title><style>"
            "body{font:15px/1.5 Inter,Arial,sans-serif;max-width:820px;margin:32px auto;padding:0 20px;color:#242824}"
            "h1{font-size:1.6rem;margin:0 0 4px}.m{color:#5b645e;font-size:.9rem}.k{display:flex;gap:10px;margin:16px 0;flex-wrap:wrap}"
            ".k div{background:#F1F4EF;border-radius:12px;padding:10px 14px;min-width:120px}.k b{display:block;font-size:1.4rem}"
            ".c{border:1px solid #E1E6DF;border-radius:14px;padding:12px 16px;margin:12px 0;break-inside:avoid}"
            ".h{display:flex;gap:10px;align-items:baseline}.h span{color:#8a4b00}.h i{margin-left:auto;color:#5b645e;font-style:normal}"
            ".q{background:#F7F9F6;border-left:3px solid #56C9C1;padding:6px 10px;margin:8px 0}</style>"
            f"<h1>Guideline health report</h1><div class='m'>{e(ws_name)} · generated {e(h['generated_at'].replace('T', ' '))}</div>"
            f"<div class='k'><div><b>{h['n_rules']}</b>rules in scope</div><div><b>{h['n_clear']}</b>tested and clear</div>"
            f"<div><b>{h['n_ambiguous']}</b>ambiguous</div><div><b>{h['n_conflicts']}</b>open conflicts</div>"
            f"<div><b>{len(h['gaps'])}</b>contexts with no rule</div></div>"
            f"<p class='m'>Priority score: {e(FORMULA)}. Scores rank the work; they do not say a rule is wrong. "
            f"Proposed wordings are suggestions for a Brand Manager to accept or change.</p>{cards}")
