"""The real-guideline benchmark items: structure, labels, per-source scoring."""
from modules import evaluation as ev


def test_public_guideline_set_is_labelled_and_scored_per_source(env):
    info = ev.public_info()
    assert info and len(info["sources"]) == 3
    items = [it for s in info["sources"] for it in s["items"]]
    assert len(items) >= 290 and {it["label"] for it in items} == {"clear", "ambiguous"}
    assert len({it["text"].lower() for it in items}) == len(items)          # no duplicates
    assert all(10 < len(it["text"]) < 400 for it in items)
    res = ev.run_all(env["ws"] if isinstance(env, dict) and "ws" in env else 1)
    assert res["counts"]["rules"] >= 314
    names = {s["name"] for s in info["sources"]}
    assert names <= set(res["by_source"])
    assert all(res["by_source"][n]["rules"]["n"] > 0 for n in names)
