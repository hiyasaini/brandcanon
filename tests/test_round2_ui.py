"""Data behind the Round 2 demo views: the cited source page and the guided-demo steps (ticked only from stored records)."""
from database import repositories as repo
from modules import approval_workflow as aw, brand_constitution, conflict_detection, content_audit as ca, demo, rule_probe
from modules.demo import DEMO_POST


def test_source_page_shows_the_cited_passage(loaded):
    res = ca.run(loaded["ws"], DEMO_POST, "Instagram", "Social media caption", "NovaTech X1", use_ai=False)
    f = next(x for x in res["findings"] if x["classification"] == "Contradicted")
    page = repo.source_page(f["passage_id"])
    assert page["doc_title"].startswith("NovaTech Product Specification") and page["location"] == "p.3"
    cited = [p for p in page["passages"] if p["id"] == f["passage_id"]]
    assert len(cited) == 1 and "12 hours" in cited[0]["text"]
    assert len(page["passages"]) > 1, "the whole stored page is shown, not just the quote"
    assert [p["seq"] for p in page["passages"]] == sorted(p["seq"] for p in page["passages"])
    assert repo.source_page(10 ** 9) is None


def test_guided_demo_steps_follow_stored_records(env):
    from ui import tour
    ws = demo.reset(with_history=False)
    u = {x["name"]: x["id"] for x in repo.users(ws)}
    done = lambda: [s["done"] for s in tour._steps(ws)]  # noqa: E731
    assert done() == [False] * 6

    demo.upload_samples(ws, u["Neha"])
    assert done()[0] is False, "uploading alone is not enough: documents must be approved"
    brand_constitution.approve_all_pending(ws, u["Neha"], 3)
    assert done()[:2] == [True, False]

    cf = next(c for c in repo.list_conflicts(ws, "open") if c["kind"] == "fact")
    spec = next(s for s in repo.conflict_sides(cf["id"]) if "Specification" in s["doc_title"])
    conflict_detection.resolve_fact_conflict(ws, u["Neha"], cf["id"], spec["id"], "Specification is the source of truth")
    assert done()[:3] == [True, True, False]

    tone = next(r for r in repo.list_rules(ws) if "friendly but professional" in r["text"])
    tid = rule_probe.run_test(ws, u["Neha"], tone["id"], "All content", "NovaTech X1")
    assert done()[2] is False, "running a test is not the step: a person must save, send or act on the investigation"
    rule_probe.resolve_test(ws, u["Neha"], tid, "clarify", "Agreed with the brand team",
                            "Maintain a friendly but professional tone: conversational, no slang.")
    assert done()[:4] == [True, True, True, False]

    sid = aw.create_draft(ws, u["Priya"], "Post", DEMO_POST, "Social media caption", "Instagram", "NovaTech X1", "",
                          use_ai=False)[0]
    assert done()[3] is False, "a draft is not yet submitted"
    aw.submit(ws, u["Priya"], sid)
    steps = tour._steps(ws)
    assert [s["done"] for s in steps][:5] == [True, True, True, True, False] and steps[4]["state"] == {"dm_sub": sid}
    aw.decide(ws, u["Kavya"], sid, "Approved", "Matches the specification.")
    assert done() == [True] * 5 + [False]
    assert [s["who"] for s in steps] == ["Neha", "Neha", "Neha", "Priya", "Kavya", "Neha"]


def test_comments_are_stored_per_revision(loaded):
    sid = aw.create_draft(loaded["ws"], loaded["cr"], "Post", DEMO_POST, "Social media caption", "Instagram", "NovaTech X1",
                          "", use_ai=False)[0]
    aw.comment(sid, loaded["rv"], "Please check the battery figure.", 1)
    got = repo.comments(sid)
    assert len(got) == 1 and got[0]["text"] == "Please check the battery figure." and got[0]["user_role"] == "Reviewer"
