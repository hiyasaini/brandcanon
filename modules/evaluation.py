"""Score RuleProbe and the Auditor against a hand-labelled set (precision / recall / F1). Misses are reported."""
import json

import config
from modules import ambiguity_detection as amb, conflict_detection, content_audit
from modules.knowledge_extraction import categorize, parse_constraints, scope_of

LABELLED = config.ROOT / "data" / "eval" / "labelled.json"
FLAG = {"Contradicted", "Unsupported", "Unverifiable"}


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


def run(ws, product="NovaTech X1"):
    data = json.loads(LABELLED.read_text())
    rules = []
    for it in data["rules"]:
        r = _rule(it["text"])
        r["category"] = "Brand tone" if r["category"] in ("Messaging", "Other policies") else r["category"]
        cases, pairs = amb.generate_cases(r, product)
        res = amb.evaluate_deterministic(r, cases, pairs) if pairs else []
        div = sum(1 for x in res if x["strict_verdict"] != x["lenient_verdict"]) / len(res) if res else 0
        rules.append({"text": it["text"], "label": it["label"], "pred": "ambiguous" if div >= 0.2 else "clear", "divergence": round(div, 2)})
    pairs_out = []
    for it in data["pairs"]:
        a, b = _rule(it["a"]), _rule(it["b"])
        for r in (a, b):
            if r["category"] in ("Messaging", "Other policies", "Terminology") and amb.vague_terms(r["text"]):
                r["category"] = "Brand tone"
        da, db_ = amb.rule_dims(a), amb.rule_dims(b)
        clash = [d for d in da if d in db_ and da[d] != db_[d]]
        pred = "conflict" if clash and conflict_detection.scopes_overlap(a["scope"], b["scope"]) else "none"
        pairs_out.append({"a": it["a"], "b": it["b"], "label": it["label"], "pred": pred, "dimension": ", ".join(clash)})
    claims = []
    for it in data["claims"]:
        res = content_audit.run(ws, it["text"], "Website", "Website copy", product, use_ai=False)
        hits = [f for f in res["findings"] if f["classification"] in FLAG and f["category"] in ("Product facts", "Claims")]
        claims.append({"text": it["text"], "label": it["label"], "pred": "flag" if hits else "ok", "why": hits[0]["message"] if hits else ""})
    return {"rules": {"rows": rules, "metrics": prf([(x["pred"], x["label"]) for x in rules], "ambiguous")},
            "pairs": {"rows": pairs_out, "metrics": prf([(x["pred"], x["label"]) for x in pairs_out], "conflict")},
            "claims": {"rows": claims, "metrics": prf([(x["pred"], x["label"]) for x in claims], "flag")},
            "note": data.get("note", "")}
