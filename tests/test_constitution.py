import pytest

from database import db, repositories as repo
from modules import brand_constitution as bc
from modules.access import NotAuthorised
from tests.conftest import rule_with


def test_rule_approval_rejection_and_permissions(loaded):
    ws = loaded["ws"]
    r = rule_with(ws, "plenty of emojis")  # from the low-authority presentation: still pending
    assert r["status"] == "Pending Validation"
    with pytest.raises(NotAuthorised):
        bc.set_rule_status(ws, loaded["rv"], r["id"], "Approved")
    bc.set_rule_status(ws, loaded["bm"], r["id"], "Rejected")
    assert repo.get_rule(r["id"])["status"] == "Rejected"
    bc.set_rule_status(ws, loaded["bm"], r["id"], "Approved")
    row = repo.get_rule(r["id"])
    assert row["status"] == "Approved" and row["approved_by"] == loaded["bm"]


def test_rule_edit_creates_version_and_revision(loaded):
    ws = loaded["ws"]
    r = rule_with(ws, "friendly but professional")
    v = bc.edit_rule(ws, loaded["bm"], r["id"], "Use a friendly, professional tone with at most one emoji.", "Clarified emoji use")
    row = repo.get_rule(r["id"])
    assert v == 2 and row["rule_version"] == 2 and row["constraints"]["max_emoji"] == 1
    assert len(repo.rule_revisions(r["id"])) == 2
    with pytest.raises(ValueError):
        bc.edit_rule(ws, loaded["bm"], r["id"], "Something else", "")


def test_rules_keep_document_version(loaded):
    r = rule_with(loaded["ws"], "friendly but professional")
    assert r["doc_title"] == "NovaTech Brand Guidelines" and r["doc_version"] == "1.2" and r["location"] == "p.2"


def test_delete_document_cleans_up(loaded):
    ws = loaded["ws"]
    deck = next(d for d in repo.list_documents(ws) if "Presentation" in d["title"])
    assert any("15 hours" in c["title"] for c in repo.list_conflicts(ws))
    bc.delete_document(ws, loaded["bm"], deck["id"])
    assert not any("15 hours" in c["title"] for c in repo.list_conflicts(ws)), "conflicts that referenced it are removed"
    assert db.fetch_one("SELECT COUNT(*) n FROM brand_facts WHERE version_id = ?", (deck["version_id"],))["n"] == 0


def test_document_review_does_not_auto_approve_rules(env):
    from modules import brand_constitution as bc, document_ingestion as di
    from tests.conftest import docx
    r = di.ingest(env["ws"], env["bm"], "Guide.docx", docx("Always use a warm tone."), use_ai=False)
    bc.set_document_status(env["ws"], env["bm"], r["document_id"], "Approved")
    doc = repo.list_documents(env["ws"])[0]
    assert doc["review_status"] == "Approved"
    assert all(x["status"] == "Pending Validation" for x in repo.list_rules(env["ws"])), "rules still need their own review"
    with pytest.raises(ValueError):
        bc.set_document_status(env["ws"], env["bm"], r["document_id"], "Rejected", "")
    r2 = di.ingest(env["ws"], env["bm"], "Note.docx", docx("Never use slang."), use_ai=False)
    bc.set_document_status(env["ws"], env["bm"], r2["document_id"], "Rejected", "Unofficial draft")
    assert next(x for x in repo.list_rules(env["ws"]) if "slang" in x["text"])["status"] == "Rejected"
    with pytest.raises(NotAuthorised):
        bc.set_document_status(env["ws"], env["cr"], r["document_id"], "Approved")


def test_new_version_needs_review_again_and_compares(env):
    from modules import brand_constitution as bc, document_ingestion as di
    from tests.conftest import docx
    r = di.ingest(env["ws"], env["bm"], "Guide.docx", docx("Version 1.0", "Always use formal language."), use_ai=False)
    bc.set_document_status(env["ws"], env["bm"], r["document_id"], "Approved")
    di.ingest(env["ws"], env["bm"], "Guide.docx", docx("Version 2.0", "Always use formal language.", "Never use slang."), use_ai=False)
    assert repo.list_documents(env["ws"])[0]["review_status"] == "Pending review"
    cmp = bc.compare_versions(r["document_id"])
    assert [x["text"] for x in cmp["added"]] == ["Never use slang."] and len(cmp["unchanged"]) == 1 and not cmp["removed"]
