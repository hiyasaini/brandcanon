import pytest

import config
from database import repositories as repo
from modules import approval_workflow as aw, decision_memory as dm, document_ingestion as di


def _approve_battery_post(env):
    ws = env["ws"]
    sid, rev, rid = aw.create_draft(ws, env["cr"], "Battery post", "Enjoy guaranteed 15-hour battery life.", "Social media caption",
                                    "Instagram", "NovaTech X1", use_ai=False)
    aw.submit(ws, env["cr"], sid)
    fs = repo.findings(rid)
    aw.decide(ws, env["rv"], sid, "Changes requested", "Use the approved battery figure.")
    aw.apply_and_revise(ws, env["cr"], sid, fs, {i: f["suggestion"] for i, f in enumerate(fs) if f["suggestion"]})
    aw.decide(ws, env["rv"], sid, "Approved", "Battery claim now matches the specification.")
    return sid


def test_decisions_are_saved(loaded):
    sid = _approve_battery_post(loaded)
    decs = [d for d in repo.list_decisions(loaded["ws"]) if d["submission_id"] == sid]
    kinds = {d["decision"] for d in decs}
    assert kinds == {"Approved", "Changes requested", "Finding upheld"}
    upheld = next(d for d in decs if d["decision"] == "Finding upheld" and "battery" in d["claim_text"])
    assert "15-hour battery life" in upheld["claim_text"] and upheld["source_title"] == "NovaTech Product Specification"
    assert repo.get_submission(sid)["status"] == "Approved"


def test_precedent_retrieved_for_similar_claim(loaded):
    _approve_battery_post(loaded)
    sid, rev, rid = aw.create_draft(loaded["ws"], loaded["cr"], "New post", "Enjoy guaranteed 15 hours of battery life.",
                                    "Social media caption", "Instagram", "NovaTech X1", use_ai=False)
    _, fs = aw.report_with_context(loaded["ws"], rev, exclude_submission=sid)
    f = next(x for x in fs if x["classification"] == "Contradicted")
    assert f["precedents"] and "flagged and corrected" in f["precedents"][0]["summary"]


def test_precedent_from_old_source_version_is_flagged(loaded):
    _approve_battery_post(loaded)
    spec = (config.SAMPLE_DIR / "NovaTech_Product_Specification.pdf").read_bytes()
    di.ingest(loaded["ws"], loaded["bm"], "NovaTech_Product_Specification.pdf", spec, use_ai=False)  # new version
    f = {"quote": "guaranteed 15 hours of battery life", "category": "Product facts", "classification": "Contradicted"}
    p = dm.precedents_for(loaded["ws"], f, "NovaTech X1", "Instagram")
    assert p and p[0]["stale"] and "no longer the current version" in p[0]["summary"]


def test_decisions_never_change_rules(loaded):
    before = [(r["id"], r["text"], r["status"]) for r in repo.list_rules(loaded["ws"])]
    _approve_battery_post(loaded)
    assert [(r["id"], r["text"], r["status"]) for r in repo.list_rules(loaded["ws"])] == before


def test_override_supersedes_earlier_decision(loaded):
    _approve_battery_post(loaded)
    old = next(d for d in repo.list_decisions(loaded["ws"]) if d["decision"] == "Finding upheld")
    with pytest.raises(ValueError):
        dm.override(loaded["ws"], loaded["rv"], old["id"], " ")
    new = dm.override(loaded["ws"], loaded["rv"], old["id"], "Battery figures changed in the new spec")
    active = {d["id"] for d in dm.active_decisions(loaded["ws"])}
    assert new in active and old["id"] not in active


def test_creator_cannot_approve(loaded):
    sid, _, _ = aw.create_draft(loaded["ws"], loaded["cr"], "x", "Meet NovaTech X1.", "Website copy", "Website", "NovaTech X1", use_ai=False)
    aw.submit(loaded["ws"], loaded["cr"], sid)
    with pytest.raises(PermissionError):
        aw.decide(loaded["ws"], loaded["cr"], sid, "Approved", "looks fine")
    with pytest.raises(ValueError):
        aw.decide(loaded["ws"], loaded["rv"], sid, "Approved", "")
