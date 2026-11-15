"""Measured accuracy benchmark: score RuleProbe and the Auditor against hand-labelled items (precision / recall / F1).

* The team's built-in set (data/eval/labelled.json) is written for the fictional NovaTech brand and is always included.
* A team can import more hand-labelled items (modules.benchmark), each tagged with where it came from, and they are scored
  separately so a high score on easy items never hides a low one on real guidelines.
* Engines: "built-in" is BrandCanon's own logic. "gemini" re-runs the claim checks with live Gemini added, so the two can be
  compared on the same items. A Gemini failure is counted and shown; it is never scored as if it had answered.
Misses are reported, not hidden.
"""
import json

import config
from modules import ambiguity_detection as amb, conflict_detection, content_audit
from modules.knowledge_extraction import categorize, parse_constraints, scope_of
from services import gemini_service

LABELLED = config.ROOT / "data" / "eval" / "labelled.json"
PUBLIC = config.ROOT / "data" / "eval" / "public_guidelines.json"   # sentences from three real public style guides
FLAG = {"Contradicted", "Unsupported", "Unverifiable"}
BASE_SOURCE = "Team-labelled · NovaTech (fictional)"
LABELS = {"rules": ("ambiguous", "clear"), "pairs": ("conflict", "none"), "claims": ("flag", "ok")}
POSITIVE = {"rules": "ambiguous", "pairs": "conflict", "claims": "flag"}


def prf(pairs, positive):
    tp = sum(1 for p, g in pairs if p == positive and g == positive)
    fp = sum(1 for p, g in pairs if p == positive and g != positive)
    fn = sum(1 for p, g in pairs if p != positive and g == positive)
    tn = len(pairs) - tp - fp - fn
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(prec, 2), "recall": round(rec, 2),
            "f1": round(2 * prec * rec / (prec + rec), 2) if prec + rec else 0.0}


def _rule(text):
    return {"text": text, "constraints": parse_constraints(text), "scope": scope_of(text), "category": categorize(text)}


def base_items():
    data = json.loads(LABELLED.read_text(encoding="utf-8"))
    items = {k: [dict(it, source=BASE_SOURCE) for it in data[k]] for k in ("rules", "pairs", "claims")}
    if PUBLIC.exists():
        for src in json.loads(PUBLIC.read_text(encoding="utf-8"))["sources"]:
            items["rules"] += [dict(it, source=src["name"]) for it in src["items"]]
    return items, data.get("note", "")


def public_info():
    """The note and labelling rubric that travel with the real-guideline items (None if the file is absent)."""
    return json.loads(PUBLIC.read_text(encoding="utf-8")) if PUBLIC.exists() else None


def _rules(items):
    out = []
    for it in items:
        r = _rule(it["text"])
        r["category"] = "Brand tone" if r["category"] in ("Messaging", "Other policies") else r["category"]
        cases, pairs = amb.generate_cases(r, it.get("product") or "NovaTech X1")
        res = amb.evaluate_deterministic(r, cases, pairs) if pairs else []
        div = sum(1 for x in res if x["strict_verdict"] != x["lenient_verdict"]) / len(res) if res else 0
        out.append({"text": it["text"], "label": it["label"], "pred": "ambiguous" if div >= 0.2 else "clear",
                    "divergence": round(div, 2), "source": it["source"]})
    return out


def _pairs(items):
    out = []
    for it in items:
        a, b = _rule(it["a"]), _rule(it["b"])
        for r in (a, b):
            if r["category"] in ("Messaging", "Other policies", "Terminology") and amb.vague_terms(r["text"]):
                r["category"] = "Brand tone"
        da, db_ = amb.rule_dims(a), amb.rule_dims(b)
        clash = [d for d in da if d in db_ and da[d] != db_[d]]
        pred = "conflict" if clash and conflict_detection.scopes_overlap(a["scope"], b["scope"]) else "none"
        out.append({"a": it["a"], "b": it["b"], "label": it["label"], "pred": pred, "dimension": ", ".join(clash),
                    "source": it["source"]})
    return out


def _claims(items, ws_of, product_of, use_ai):
    out, failed = [], 0
    for it in items:
        res = content_audit.run(ws_of(it), it["text"], "Website", "Website copy", it.get("product") or product_of(it), use_ai=use_ai)
        if use_ai and gemini_service.is_failure(res["engine"]):
            failed += 1
            out.append({"text": it["text"], "label": it["label"], "pred": "gemini failed", "why": res["ai_error"] or res["engine"],
                        "source": it["source"]})
            continue
        hits = [f for f in res["findings"] if f["classification"] in FLAG and f["category"] in ("Product facts", "Claims")]
        out.append({"text": it["text"], "label": it["label"], "pred": "flag" if hits else "ok",
                    "why": hits[0]["message"] if hits else "", "source": it["source"]})
    return out, failed


def _metrics(rows, kind):
    scored = [(x["pred"], x["label"]) for x in rows if x["pred"] != "gemini failed"]
    return prf(scored, POSITIVE[kind])


def run_all(demo_ws, extra=None, use_ai=False, product="NovaTech X1"):
    """Score the built-in set (against the NovaTech demo workspace) plus any imported sets (each against the workspace it was
    imported into). `extra`: rows from benchmark.sets(). Returns rows and metrics overall and per source."""
    items, note = base_items()
    for e in extra or []:
        for it in json.loads(e["payload"]):
            items[e["kind"]].append(dict(it, source=e["source"], _ws=e["workspace_id"]))
    rules = _rules(items["rules"])
    pairs = _pairs(items["pairs"])
    from modules import rule_probe
    claims, failed = _claims(items["claims"], lambda it: it.get("_ws") or demo_ws,
                             lambda it: rule_probe.main_product(it.get("_ws") or demo_ws) if it.get("_ws") else product, use_ai)
    out = {"rules": {"rows": rules, "metrics": _metrics(rules, "rules")},
           "pairs": {"rows": pairs, "metrics": _metrics(pairs, "pairs")},
           "claims": {"rows": claims, "metrics": _metrics(claims, "claims")},
           "note": note, "engine": "gemini" if use_ai else "built-in", "gemini_failed": failed}
    sources = sorted({x["source"] for k in ("rules", "pairs", "claims") for x in out[k]["rows"]}, key=lambda s: (s != BASE_SOURCE, s))
    out["by_source"] = {s: {k: {**_metrics([x for x in out[k]["rows"] if x["source"] == s], k),
                                "n": sum(1 for x in out[k]["rows"] if x["source"] == s)} for k in ("rules", "pairs", "claims")}
                        for s in sources}
    out["counts"] = {k: len(out[k]["rows"]) for k in ("rules", "pairs", "claims")}
    return out


def run(ws, product="NovaTech X1"):
    """The built-in set only (kept for the original callers and tests)."""
    return run_all(ws, None, False, product)
