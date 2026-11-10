import pytest

from database import repositories as repo
from modules import conflict_detection as cd


def test_battery_conflict_detected_with_both_sources(loaded):
    c = next(x for x in repo.list_conflicts(loaded["ws"], "open") if "battery life" in x["title"])
    sides = repo.conflict_sides(c["id"])
    vals = {s["value"]: s["doc_title"] for s in sides}
    assert vals == {12.0: "NovaTech Product Specification", 15.0: "NovaTech Marketing Presentation 2025"}
    assert "has not chosen" in c["explanation"], "BrandCanon must not silently pick a source"


def test_resolving_fact_conflict_supersedes_other_value(loaded):
    ws = loaded["ws"]
    c = next(x for x in repo.list_conflicts(ws, "open") if "battery life" in x["title"])
    spec = next(s for s in repo.conflict_sides(c["id"]) if s["value"] == 12)
    with pytest.raises(ValueError):
        cd.resolve_fact_conflict(ws, loaded["bm"], c["id"], spec["id"], "")
    cd.resolve_fact_conflict(ws, loaded["bm"], c["id"], spec["id"], "Specification is authoritative")
    statuses = {s["value"]: s["status"] for s in repo.conflict_sides(c["id"])}
    assert statuses == {12.0: "Approved", 15.0: "Superseded"}
    assert db_status(ws, c["id"]) == "resolved"


def db_status(ws, cid):
    return next(x for x in repo.list_conflicts(ws) if x["id"] == cid)["status"]


def test_rule_conflict_needs_overlapping_scope(loaded):
    titles = [c["title"] for c in repo.list_conflicts(loaded["ws"])]
    assert any("Formality" in t for t in titles)
    assert cd.scopes_overlap("All content", "Instagram")
    assert cd.scopes_overlap("Social media", "Instagram")
    assert not cd.scopes_overlap("Email marketing", "Instagram")


def test_rescope_resolves_rule_conflict(loaded):
    ws = loaded["ws"]
    c = next(x for x in repo.list_conflicts(ws, "open") if x["kind"] == "rule")
    target = repo.conflict_sides(c["id"])[0]
    cd.resolve_rule_conflict(ws, loaded["bm"], c["id"], "rescope", "Formal only in email", target["id"], "Email marketing")
    assert repo.get_rule(target["id"])["scope"] == "Email marketing"
    assert db_status(ws, c["id"]) == "resolved"


def test_coverage_gaps_report_missing_guidance(loaded):
    gaps = cd.coverage_gaps(loaded["ws"])
    assert "Influencer partnerships" in gaps and "Instagram" not in gaps
