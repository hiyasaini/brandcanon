import pytest

from database import repositories as repo
from modules import ambiguity_detection as amb, rule_probe
from services import gemini_service, validation_service as vs
from tests.conftest import rule_with


def test_controlled_cases_change_one_characteristic(loaded):
    r = rule_with(loaded["ws"], "friendly but professional")
    cases, pairs = amb.generate_cases(r, "NovaTech X1")
    assert cases[0]["dimension"] == "baseline"
    for c in cases[1:]:
        others = [d for d in pairs if d != c["dimension"]]
        assert amb.level(c["dimension"], c["example"]) == c["level"], c
        assert all(amb.level(d, c["example"]) == 0 for d in others), f"{c['example']} changes more than one characteristic"
    again, _ = amb.generate_cases(r, "NovaTech X1")
    assert [c["example"] for c in again] == [c["example"] for c in cases], "test cases must be reproducible"


def test_vague_tone_rule_is_classified_ambiguous(loaded):
    ws = loaded["ws"]
    r = rule_with(ws, "friendly but professional")
    tid = rule_probe.run_test(ws, loaded["bm"], r["id"], "All content")
    t = repo.latest_test(r["id"])
    assert t["id"] == tid and t["classification"] == "Ambiguous rule" and t["divergence"] >= 0.2
    assert t["recommendation"] and t["requires_human_review"] == 1
    after = repo.get_rule(r["id"])
    assert after["status"] == r["status"] and after["text"] == r["text"], "a test never changes the rule itself"
    assert after["clarity"] == "Ambiguous" and t["investigation_state"] == "draft"
    assert len(repo.test_cases(tid)) == 5


def test_clarification_removes_divergence_and_keeps_history(loaded):
    ws, bm = loaded["ws"], loaded["bm"]
    r = rule_with(ws, "friendly but professional")
    tid = rule_probe.run_test(ws, bm, r["id"])
    t = repo.latest_test(r["id"])
    ver = rule_probe.resolve_test(ws, bm, tid, "clarify", "Agreed with brand team", t["recommendation"])
    assert ver == 2
    rule_probe.run_test(ws, bm, r["id"])
    tests = repo.tests_for_rule(r["id"])
    assert len(tests) == 2 and tests[0]["rule_version"] == 2 and tests[0]["divergence"] == 0
    assert tests[1]["status"] == "resolved" and tests[1]["resolution"] == "clarify"


def test_missing_guidance_for_out_of_scope_context(loaded):
    ws = loaded["ws"]
    r = rule_with(ws, "casual language in every social media post")
    rule_probe.run_test(ws, loaded["bm"], r["id"], "Influencer partnerships")
    assert repo.latest_test(r["id"])["classification"] == "Missing guidance"


def test_contradictory_rules_classification(loaded):
    ws = loaded["ws"]
    r = rule_with(ws, "pressure phrases")
    rule_probe.run_test(ws, loaded["bm"], r["id"])
    assert repo.latest_test(r["id"])["classification"] == "Contradictory rules"


def test_measurable_rule_is_clear(loaded):
    ws = loaded["ws"]
    r = rule_with(ws, "sentences under 25 words")
    rule_probe.run_test(ws, loaded["bm"], r["id"], "Email marketing")
    assert repo.latest_test(r["id"])["classification"] == "Clear rule"


def test_model_uncertainty_is_separate_from_ambiguity(loaded, monkeypatch):
    """Simulated model whose repeated passes disagree -> 'Model uncertainty', not 'Ambiguous rule'."""
    ws = loaded["ws"]
    r = rule_with(ws, "friendly but professional")
    calls = {"n": 0}

    def fake_generate(prompt, schema, **kw):
        if schema is vs.CaseVerdicts:
            calls["n"] += 1
            v = "pass" if calls["n"] % 2 else "fail"   # flip between passes, same for both readings
            return vs.CaseVerdicts(results=[{"id": i, "verdict": v, "reason": "simulated"} for i in range(1, 10)])
        return None
    monkeypatch.setattr(gemini_service, "enabled", lambda: True)
    monkeypatch.setattr(gemini_service, "generate", fake_generate)
    rule_probe.run_test(ws, loaded["bm"], r["id"])
    t = repo.latest_test(r["id"])
    assert t["classification"] == "Model uncertainty" and t["self_inconsistency"] >= 0.3
    assert t["engine"].startswith("Live Gemini")


def test_reviewer_marks_and_permissions(loaded):
    ws = loaded["ws"]
    r = rule_with(ws, "friendly but professional")
    tid = rule_probe.run_test(ws, loaded["rv"], r["id"])
    case = repo.test_cases(tid)[1]
    rule_probe.mark_case(ws, loaded["rv"], case["id"], "inconclusive")
    assert repo.test_cases(tid)[1]["reviewer_mark"] == "inconclusive"
    with pytest.raises(PermissionError):
        rule_probe.run_test(ws, loaded["cr"], r["id"])
    with pytest.raises(PermissionError):
        rule_probe.resolve_test(ws, loaded["rv"], tid, "keep", "fine")


def test_investigation_workflow_and_labels(loaded):
    """Save → send for human review → approve interpretation; reviewers cannot change the rule; labels match the brief."""
    from modules.access import NotAuthorised
    ws, bm, rv = loaded["ws"], loaded["bm"], loaded["rv"]
    r = rule_with(ws, "friendly but professional")
    tid = rule_probe.run_test(ws, rv, r["id"])
    assert {c["assessment"] for c in repo.test_cases(tid)} <= {"Likely compliant", "Potential violation", "Uncertain", "Needs human review"}
    assert any(x["rule"]["id"] == r["id"] for x in rule_probe.open_findings(ws))
    rule_probe.save_investigation(ws, rv, tid, "Checked cases 2 and 5")
    assert repo.latest_test(r["id"])["investigation_state"] == "saved"
    with pytest.raises(ValueError):
        rule_probe.send_for_review(ws, rv, tid, "")
    rule_probe.send_for_review(ws, rv, tid, "Formality boundary needs a brand decision")
    assert repo.latest_test(r["id"])["investigation_state"] == "in_review"
    with pytest.raises(NotAuthorised):
        rule_probe.resolve_test(ws, rv, tid, "keep", "Reviewer cannot decide")
    rule_probe.resolve_test(ws, bm, tid, "keep", "Readable as written for our audience")
    t = repo.latest_test(r["id"])
    assert t["investigation_state"] == "approved" and repo.get_rule(r["id"])["text"] == r["text"]
    assert not any(x["rule"]["id"] == r["id"] for x in rule_probe.open_findings(ws))
    with pytest.raises(ValueError):
        rule_probe.send_for_review(ws, rv, tid, "too late")
    assert [e["label"] for e in rule_probe.timeline(tid)][-1] == "Resolved RuleProbe finding"


def test_manual_and_edited_cases(loaded):
    ws, bm = loaded["ws"], loaded["bm"]
    r = rule_with(ws, "friendly but professional")
    cases = rule_probe.preview_cases(ws, r["id"])
    assert cases and cases[0]["dimension"] == "baseline"
    cases.append({"example": "Yo! NovaTech X1 is lit, grab it now!!!", "dimension": "manual"})
    tid = rule_probe.run_test(ws, bm, r["id"], cases=cases)
    stored = repo.test_cases(tid)
    assert stored[-1]["dimension"] == "manual" and stored[-1]["example"].startswith("Yo!")
    with pytest.raises(ValueError):
        rule_probe.run_test(ws, bm, r["id"], cases=[{"example": "x" * 401}])
    # a rule with no measurable characteristic: manual cases are marked uncertain, never guessed
    from modules import document_ingestion as di
    from tests.conftest import docx
    di.ingest(ws, bm, "Voice_Note.docx", docx("Copy must feel authentic."), use_ai=False)
    other = rule_with(ws, "feel authentic")
    assert not rule_probe.preview_cases(ws, other["id"])
    tid2 = rule_probe.run_test(ws, bm, other["id"], cases=[{"example": "NovaTech X1 is a thoughtful laptop."}])
    assert all(c["assessment"] == "Uncertain" for c in repo.test_cases(tid2))
