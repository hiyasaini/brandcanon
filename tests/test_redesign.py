"""Backend pieces added with the redesign: manual rules, the knowledge graph, global search and review-time statistics."""
import pytest

from database import db, repositories as repo
from modules import approval_workflow as aw, brand_constitution as bc, demo, governance_analytics as ga
from modules import knowledge_graph as kg, search
from modules.demo import DEMO_POST


def test_manual_rule_is_pending_unless_approved(loaded):
    ws, bm = loaded["ws"], loaded["bm"]
    rid = bc.add_rule(ws, bm, "Always write the product name as NovaTech X1.", "Terminology", "All content", "Brand review 12 Nov")
    r = repo.get_rule(rid)
    assert r["status"] == "Pending Validation" and r["version_id"] is None and r["extracted_by"].startswith("manual")
    assert repo.rule_revisions(rid)[0]["reason"].startswith("Added manually")
    rid2 = bc.add_rule(ws, bm, "Use sentence case in headlines.", "Brand tone", "Website", "Style guide update", approve=True)
    assert repo.get_rule(rid2)["status"] == "Approved" and repo.get_rule(rid2)["approved_by"] == bm
    with pytest.raises(ValueError):
        bc.add_rule(ws, bm, "Use sentence case.", "Brand tone", "All content", "")       # a reason is required
    with pytest.raises(ValueError):
        bc.add_rule(ws, bm, "Use sentence case.", "Not a category", "All content", "x")
    with pytest.raises(PermissionError):
        bc.add_rule(ws, loaded["cr"], "Use sentence case.", "Brand tone", "All content", "x")


def test_graph_uses_only_stored_records(env):
    ws = demo.reset(with_history=True)
    G = kg.build(ws)
    ids = {n["id"] for n in G["nodes"]}
    assert G["edges"] and all(e["source"] in ids and e["target"] in ids for e in G["edges"])
    assert all(e["rel"] in kg.RELATIONS for e in G["edges"])
    count = lambda kind: sum(n["kind"] == kind for n in G["nodes"])  # noqa: E731
    assert count("document") == db.fetch_one("SELECT COUNT(*) n FROM documents WHERE workspace_id = ? AND status = 'active'", (ws,))["n"]
    assert count("decision") == db.fetch_one("SELECT COUNT(*) n FROM decisions WHERE workspace_id = ?", (ws,))["n"]
    # every 'contains' edge matches the rule's stored source document
    for e in G["edges"]:
        if e["rel"] == "contains":
            rule = repo.get_rule(int(e["target"].split(":")[1]))
            assert rule["document_id"] == int(e["source"].split(":")[1])
        if e["rel"] == "applies_to":
            d = db.fetch_one("SELECT rule_id FROM decisions WHERE id = ?", (int(e["source"].split(":")[1]),))
            assert d["rule_id"] == int(e["target"].split(":")[1])
    # every node can be opened somewhere
    assert all(n["open"] for n in G["nodes"])


def test_graph_filters_layouts_and_neighbours(env):
    ws = demo.reset(with_history=True)
    G = kg.build(ws)
    only = kg.subgraph(G, ["document", "rule"], ["contains"])
    assert {n["kind"] for n in only["nodes"]} <= {"document", "rule"} and {e["rel"] for e in only["edges"]} == {"contains"}
    doc = next(n["id"] for n in G["nodes"] if n["kind"] == "document")
    focus = kg.subgraph(G, focus=doc, depth=1)
    nb = {doc} | {e["target"] for e in G["edges"] if e["source"] == doc} | {e["source"] for e in G["edges"] if e["target"] == doc}
    assert {n["id"] for n in focus["nodes"]} == nb
    found = kg.subgraph(G, query="battery")
    assert found["seeds"] and all(any(s == n["id"] for n in found["nodes"]) for s in found["seeds"])
    for kind in ("force", "circular", "hierarchical", "grid"):
        pos = kg.layout(G, kind)
        assert set(pos) == {n["id"] for n in G["nodes"]}
    assert kg.layout(G, "force") == kg.layout(G, "force"), "same records → same picture"
    assert kg.neighbours(G, doc)
    assert kg.build(ws) == G


def test_global_search_finds_stored_text_only(loaded):
    ws = loaded["ws"]
    res = search.search(ws, "battery")
    assert res and all(item["page"] in ("constitution", "auditor", "decisions") for v in res.values() for item in v)
    assert search.search(ws, "zzqqxx-not-anywhere") == {}
    assert search.search(ws, "a") == {}, "very short queries are ignored"


def test_average_review_time(loaded):
    ws = loaded["ws"]
    assert ga.review_time_stats(ws) == (None, None, 0)
    sid = aw.create_draft(ws, loaded["cr"], "Post", DEMO_POST, "Social media caption", "Instagram", "NovaTech X1", "",
                          use_ai=False)[0]
    aw.submit(ws, loaded["cr"], sid)
    aw.decide(ws, loaded["rv"], sid, "Approved", "Fine.")
    mean, median, n = ga.review_time_stats(ws)
    assert n == 1 and mean is not None and mean == median and mean >= 0
