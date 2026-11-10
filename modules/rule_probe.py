"""RuleProbe: test a brand rule in a chosen context before trusting it to judge content.

Workflow: select rule + context → retrieve related rules & sources → generate controlled cases (editable, plus any the
reviewer writes) → evaluate under a strict and a lenient reading → classify as a POTENTIAL finding → save the
investigation / send it for human review → a Brand Manager approves the interpretation or updates the rule (a new
version) → re-run.

Safeguards: disagreement between readings is evidence, not proof; model self-disagreement is reported separately as
model uncertainty; running a test never changes a rule's approval status or wording.
"""
import json

from database import db, repositories as repo
from modules import ambiguity_detection as amb
from modules import brand_constitution, conflict_detection, evidence_retrieval
from modules.access import require
from services import gemini_service, validation_service as vs

AMBIGUITY_THRESHOLD = 0.2      # share of cases where readings disagree
UNCERTAINTY_THRESHOLD = 0.3    # share of cases where repeated model passes disagree


def related_rules(ws, rule, k=5):
    """Rules that share a tested characteristic or wording with this rule (excluding itself)."""
    dims = amb.rule_dims(rule)
    out = []
    for r in repo.list_rules(ws, ("Approved", "Pending Validation", "Needs Clarification")):
        if r["id"] == rule["id"]:
            continue
        shared = set(dims) & set(amb.rule_dims(r))
        if shared and conflict_detection.scopes_overlap(rule["scope"], r["scope"]):
            out.append((len(shared) + 1, r))
    for hit in evidence_retrieval.search_rules(ws, rule["text"], k=k):
        if hit["id"] != rule["id"] and all(hit["id"] != r["id"] for _, r in out):
            out.append((hit["score"] / 10, hit))
    out.sort(key=lambda x: -x[0])
    return [r for _, r in out[:k]]


def _gemini_cases(rule, product, context, vague):
    """Ask Gemini for controlled examples for undefined words the deterministic lexicon cannot vary.

    Each variant must change only how strongly ONE of the rule's undefined words is expressed. Variants for words that
    are not in the rule are dropped; fewer than two usable variants is reported as a malformed response (and not cached).
    """
    allowed = {v.lower() for v in vague}

    def to_cases(res):
        seen, cases = {res.baseline.strip().lower()}, [{"dimension": "baseline", "level": 0, "example": res.baseline.strip()}]
        for v in res.variants:
            ex = v.example.strip()
            if v.aspect.strip().lower() in allowed and ex.lower() not in seen:
                seen.add(ex.lower())
                cases.append({"dimension": amb.AI_PREFIX + v.aspect.strip().lower(), "level": v.level, "example": ex})
        if len(cases) < 3:
            raise gemini_service.GeminiError("malformed", "Gemini's test examples did not vary the rule's undefined words, "
                                                          "so they were discarded.")
        return cases

    res = gemini_service.generate(
        f"A brand rule uses undefined words: {', '.join(vague)}. Context: {context}. Product: {product}.\n"
        "Write ONE neutral baseline marketing sentence about the product, then variants of that same sentence. Each variant "
        "must change ONLY how strongly one of the undefined words is expressed (level 1 = mild, level 2 = strong) and keep "
        "everything else identical. Do not add prices, numbers, specifications or claims.\n"
        'Return JSON {"baseline": str, "variants": [{"aspect": one of the undefined words, "level": 1|2, "example": str}]}\n'
        f"Rule:\n{gemini_service.untrusted(rule['text'])}", vs.GeneratedCases, temperature=0.4, check=to_cases)
    return to_cases(res)


def _gemini_evaluate(rule, cases, context):
    lines = "\n".join(f"{i + 1}. {c['example']}" for i, c in enumerate(cases))
    readings = {}
    for reading, instr in (("strict", "Interpret every undefined word in the rule as narrowly as a cautious brand manager would."),
                           ("lenient", "Interpret every undefined word in the rule as broadly as a creative copywriter reasonably would.")):
        runs = []
        for p in range(3):
            res = gemini_service.generate(
                f"Brand rule (context: {context}):\n{gemini_service.untrusted(rule['text'])}\n"
                f"Reading: {reading.upper()}. {instr}\nFor each numbered example decide pass, fail or unclear and give a short reason. "
                f"(independent evaluation {p + 1})\nReturn JSON {{\"results\":[{{\"id\":int,\"verdict\":\"pass|fail|unclear\",\"reason\":str}}]}}\n"
                f"Examples:\n{gemini_service.untrusted(lines)}", vs.CaseVerdicts, temperature=0.6)
            runs.append({r.id: r for r in res.results})
        readings[reading] = runs
    out = []
    for i, c in enumerate(cases, 1):
        res = {}
        votes_strict = []
        for reading, runs in readings.items():
            votes = [run[i].verdict if i in run else "unclear" for run in runs]
            maj = max(set(votes), key=votes.count)
            reason = next((run[i].reason for run in runs if i in run and run[i].verdict == maj), "No reason returned.")
            res[reading] = (maj, reason)
            if reading == "strict":
                votes_strict = votes
        out.append(amb._finish(c, res["strict"], res["lenient"], votes_strict))
    return out


def main_product(ws):
    row = db.fetch_one("""SELECT product, COUNT(*) n FROM brand_facts WHERE workspace_id = ? AND status != 'Rejected'
                          GROUP BY product ORDER BY n DESC LIMIT 1""", (ws,))
    return row["product"] if row else "our product"


MAX_CASES = 14


def preview_cases(ws, rule_id, product=None):
    """The controlled examples RuleProbe would generate (each changes one characteristic), for review and editing."""
    rule = repo.get_rule(rule_id)
    cases, pairs = amb.generate_cases(rule, product or main_product(ws))
    return cases if pairs else []


def _clean_cases(cases):
    out = []
    for x in cases or []:
        ex = " ".join(str(x.get("example") or "").split())
        if not ex:
            continue
        if len(ex) > 400:
            raise ValueError("Each test case must be 400 characters or fewer.")
        out.append({"dimension": x.get("dimension") or "manual", "level": int(x.get("level") or 0), "example": ex})
    if len(out) > MAX_CASES:
        raise ValueError(f"Use at most {MAX_CASES} test cases.")
    return out


def _evaluate_without_model(rule, cases, pairs):
    """Deterministic verdicts. Without measurable characteristics a case is marked uncertain, never guessed."""
    if pairs:
        return amb.evaluate_deterministic(rule, cases, pairs)
    why = ("Deterministic logic cannot judge this rule's subjective wording. Review it yourself, or enable live Gemini.")
    return [amb._finish(c, ("unclear", why), ("unclear", why), ["x"]) for c in cases]


def run_test(ws, user_id, rule_id, context="All content", product=None, cases=None):
    """Run RuleProbe and store a rule_tests row with its cases. Returns the test id.

    `cases` (optional): the examples to evaluate — the generated controlled cases, possibly edited, plus manual ones
    (dimension 'manual'). When omitted, the controlled cases are generated.
    """
    require(user_id, "Brand Manager", "Reviewer")
    rule = repo.get_rule(rule_id)
    product = product or main_product(ws)
    generated, pairs = amb.generate_cases(rule, product)
    custom = _clean_cases(cases) if cases is not None else None
    cases = custom if custom else generated
    vague = amb.vague_terms(rule["text"])
    testable = rule["category"] in amb.TESTABLE_CATEGORIES
    engine, results, ai_error = gemini_service.fallback_label(), None, None
    if gemini_service.enabled() and (pairs or custom or (vague and testable)):
        with gemini_service.tracking() as sources:
            try:
                ai_cases = _gemini_cases(rule, product, context, vague) if not pairs and not custom else None
                results = _gemini_evaluate(rule, ai_cases or cases, context)
                engine = gemini_service.label_for(sources) + (" · examples and verdicts" if ai_cases else " · verdicts on controlled examples")
            except gemini_service.GeminiError as e:
                ai_error, engine, results = e, gemini_service.fallback_label(e), None
    if results is None:
        results = _evaluate_without_model(rule, cases, pairs) if (pairs or custom) else []

    n = len(results)
    diverging = [r for r in results if r["strict_verdict"] != r["lenient_verdict"]]
    divergence = len(diverging) / n if n else 0.0
    self_inc = sum(1 for r in results if not r["self_consistent"]) / n if n else 0.0
    boundary = sorted({r["dimension"] for r in diverging if r["dimension"] != "baseline"}
                      | {d for d, v in pairs.items() if v == "toward" and any(r["dimension"] == "baseline" for r in diverging)})
    open_conf = repo.open_conflicts_for_rule(rule_id)
    in_scope = conflict_detection.scopes_overlap(rule["scope"], context)
    related = related_rules(ws, rule)
    specific = [r for r in repo.list_rules(ws, ("Approved", "Pending Validation", "Needs Clarification"))
                if r["id"] != rule["id"] and context in (r["scope"] or "").split(", ")]

    if context != "All content" and not in_scope and not specific:
        cls = "Missing guidance"
        issue = (f"{rule['code']} applies to {rule['scope']}, and no other rule covers {context}. "
                 f"There is no guidance for this context yet — BrandCanon will not invent one.")
        rec = f"Decide whether {rule['code']} should also apply to {context}, or add a rule for it."
    elif self_inc >= UNCERTAINTY_THRESHOLD:
        cls = "Model uncertainty"
        issue = (f"Repeated evaluations disagreed on {self_inc:.0%} of cases. This may reflect missing context or model "
                 "limits rather than a defective rule.")
        rec = "Review the cases manually and mark which assessments are correct."
    elif divergence >= AMBIGUITY_THRESHOLD:
        cls = "Ambiguous rule"
        labels = [amb.dim_label(d).lower() for d in boundary]
        issue = (f"Strict and lenient readings disagree on {divergence:.0%} of controlled examples. The rule does not define "
                 f"acceptable {', '.join(labels)}" + (f" (undefined terms: {', '.join(vague)})." if vague else "."))
        rec = amb.suggest_clarification(rule["text"], boundary, pairs)
        if gemini_service.enabled():
            try:
                res = gemini_service.generate(
                    "Rewrite this brand rule so it is unambiguous while keeping its intent. It must settle: "
                    + "; ".join(amb.clarify_snippet(d, pairs.get(d)) for d in boundary)
                    + f'\nReturn JSON {{"rule": str}}\nRule:\n{gemini_service.untrusted(rule["text"])}', vs.Clarification)
                rec = res.rule
                engine += " · clarification by Gemini"
            except gemini_service.GeminiError as e:
                engine += f" · clarification wording: deterministic (Gemini failed: {e.short})"
    elif open_conf:
        cls = "Contradictory rules"
        issue = (f"The wording is testable ({divergence:.0%} divergence), but it pulls against "
                 + ", ".join(c["title"] for c in open_conf) + ".")
        rec = "Resolve the conflict in the Conflicts tab: narrow a scope, archive one rule, or confirm both can coexist."
    elif not results and vague and testable:
        cls = "Model uncertainty"
        issue = (f"The rule uses subjective words ({', '.join(vague)}) that deterministic logic cannot turn into controlled tests"
                 + (f"; Gemini could not generate them either ({ai_error.short})." if ai_error else
                    (" (enable live Gemini to generate examples for them)." if not gemini_service.enabled() else ".")))
        rec = "Review manually or rephrase the rule with observable criteria."
    else:
        cls = "Clear rule"
        issue = ("Strict and lenient readings agree on every controlled example." if results
                 else "The rule is already measurable (exact terms, numbers or required elements).")
        rec = ""

    with db.transaction() as c:
        tid = db.insert("rule_tests", c=c, rule_id=rule_id, rule_version=rule["rule_version"], context=context,
                        engine=engine, classification=cls, issue=issue, recommendation=rec, divergence=round(divergence, 3),
                        self_inconsistency=round(self_inc, 3), requires_human_review=int(cls != "Clear rule"),
                        related_rule_ids=json.dumps([r["id"] for r in related]),
                        status="open" if cls != "Clear rule" else "resolved", run_by=user_id, created_at=db.now())
        for i, r in enumerate(results):
            db.insert("rule_test_cases", c=c, test_id=tid, seq=i, dimension=r["dimension"], level=r["level"],
                      example=r["example"], strict_verdict=r["strict_verdict"], strict_reason=r["strict_reason"],
                      lenient_verdict=r["lenient_verdict"], lenient_reason=r["lenient_reason"],
                      assessment=r["assessment"], confidence=r["confidence"])
        clarity = {"Clear rule": "Clear", "Ambiguous rule": "Ambiguous", "Contradictory rules": "In conflict",
                   "Missing guidance": "Missing guidance", "Model uncertainty": "Uncertain"}[cls]
        # A potential finding is recorded on the rule; its approval status and wording are never changed here.
        db.update("brand_rules", rule_id, c=c, clarity=clarity, divergence=round(divergence, 3), updated_at=db.now())
        repo.log(ws, user_id, "Ran RuleProbe", "rule_test", tid,
                 f"{rule['code']} v{rule['rule_version']} in {context}: {cls} ({divergence:.0%} divergence, {engine})", c=c)
    return tid


def mark_case(ws, user_id, case_id, mark):
    require(user_id, "Brand Manager", "Reviewer")
    if mark not in ("correct", "incorrect", "inconclusive"):
        raise ValueError("Mark must be correct, incorrect or inconclusive.")
    db.update("rule_test_cases", case_id, reviewer_mark=mark, marked_by=user_id)


def resolve_test(ws, user_id, test_id, action, note, clarified_text=None):
    """Brand Manager decision on an investigation.

    action: 'clarify' — update the rule after authorisation (saves a new version; the old one stays in history)
            'keep'    — approve the interpretation: the rule stays as written
            'needs_work' — keep the investigation open
    """
    require(user_id, "Brand Manager")
    if not (note or "").strip():
        raise ValueError("Please add a short explanation for this decision.")
    t = db.get("rule_tests", test_id)
    new_version = None
    if action == "clarify":
        new_version = brand_constitution.edit_rule(ws, user_id, t["rule_id"], clarified_text,
                                                   f"RuleProbe clarification: {note}")
        state = "rule_updated"
    elif action == "keep":
        rule = repo.get_rule(t["rule_id"])
        db.update("brand_rules", t["rule_id"], clarity="Accepted as written", updated_at=db.now(),
                  **({"status": "Approved", "approved_by": user_id, "approved_at": db.now()}
                     if rule["status"] == "Needs Clarification" else {}))
        state = "approved"
    elif action == "needs_work":
        state = "saved"
    else:
        raise ValueError(f"Unknown action {action}")
    db.update("rule_tests", test_id, status="resolved" if action != "needs_work" else "open", resolution=action,
              resolution_note=note.strip(), resolved_by=user_id, resolved_at=db.now(), investigation_state=state,
              notes=note.strip())
    repo.log(ws, user_id, "Resolved RuleProbe finding", "rule_test", test_id, f"{action}: {note[:80]}")
    return new_version


def save_investigation(ws, user_id, test_id, notes=""):
    """Keep the investigation (with the reviewer's notes) so it can be picked up later."""
    require(user_id, "Brand Manager", "Reviewer")
    t = db.get("rule_tests", test_id)
    if t["investigation_state"] in ("approved", "rule_updated"):
        raise ValueError("This investigation is already closed.")
    db.update("rule_tests", test_id, investigation_state="saved", notes=(notes or "").strip() or t["notes"])
    repo.log(ws, user_id, "Investigation updated", "rule_test", test_id, f"Saved: {(notes or '')[:80]}")


def send_for_review(ws, user_id, test_id, notes):
    """Ask a Brand Manager to review the potential finding. A note explaining why is required."""
    require(user_id, "Brand Manager", "Reviewer")
    if not (notes or "").strip():
        raise ValueError("Add a note for the reviewer explaining what needs a decision.")
    t = db.get("rule_tests", test_id)
    if t["investigation_state"] in ("approved", "rule_updated"):
        raise ValueError("This investigation is already closed.")
    db.update("rule_tests", test_id, investigation_state="in_review", notes=notes.strip())
    repo.log(ws, user_id, "Investigation updated", "rule_test", test_id, f"Sent for human review: {notes[:80]}")


def open_findings(ws):
    """Rules whose latest test (on the current wording) found a potential problem that nobody has closed yet."""
    out = []
    for r in repo.list_rules(ws, ("Approved", "Pending Validation", "Needs Clarification")):
        t = repo.latest_test(r["id"])
        if t and t["rule_version"] == r["rule_version"] and t["classification"] != "Clear rule" \
                and t["investigation_state"] not in ("approved", "rule_updated"):
            out.append({"rule": r, "test": t})
    return out


def timeline(test_id):
    """Chronological record of an investigation and of the rule it examines."""
    t = db.get("rule_tests", test_id)
    rows = db.fetch_all("""SELECT a.*, u.name user_name FROM activity_log a LEFT JOIN users u ON u.id = a.user_id
                           WHERE (a.entity_type = 'rule_test' AND a.entity_id IN
                                    (SELECT id FROM rule_tests WHERE rule_id = ?))
                              OR (a.entity_type = 'rule' AND a.entity_id = ?) ORDER BY a.id""", (t["rule_id"], t["rule_id"]))
    tone = {"Ran RuleProbe": "terracotta", "Investigation updated": "amber", "Resolved RuleProbe finding": "olive",
            "Rule revised": "olive", "Rule approved": "olive"}
    return [{"at": r["created_at"], "who": r["user_name"], "label": r["action"], "detail": r["detail"] or "",
             "tone": tone.get(r["action"], "neutral")} for r in rows]


def scan(ws, user_id, context="All content"):
    """Detect conflicts, then probe every testable live rule. Returns (n_tested, n_new_conflicts)."""
    require(user_id, "Brand Manager")
    n_conf = conflict_detection.detect(ws, user_id)
    n = 0
    for r in repo.list_rules(ws, ("Approved", "Pending Validation", "Needs Clarification")):
        if amb.rule_dims(r) or (amb.vague_terms(r["text"]) and r["category"] in amb.TESTABLE_CATEGORIES):
            run_test(ws, user_id, r["id"], context)
            n += 1
    return n, n_conf
