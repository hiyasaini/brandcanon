"""Brand Constitution: human validation, editing, versioning and lifecycle of rules, facts, terms and documents."""
import json

import config

from database import db, repositories as repo
from modules import knowledge_extraction as kx
from modules.access import require

MANAGER = "Brand Manager"


def set_rule_status(ws, user_id, rule_id, status, note=""):
    require(user_id, MANAGER)
    if status not in ("Approved", "Rejected", "Needs Clarification", "Archived", "Pending Validation"):
        raise ValueError(f"Unknown status {status}")
    rule = repo.get_rule(rule_id)
    fields = {"status": status, "updated_at": db.now()}
    if status == "Approved":
        fields.update(approved_by=user_id, approved_at=db.now())
    with db.transaction() as c:
        db.update("brand_rules", rule_id, c=c, **fields)
        repo.log(ws, user_id, f"Rule {status.lower()}", "rule", rule_id, f"{rule['code']}: {note or rule['text'][:80]}", c=c)


def approve_all_pending(ws, user_id, min_authority_rank=0):
    require(user_id, MANAGER)
    n = 0
    with db.transaction() as c:
        for r in c.execute("""SELECT r.id FROM brand_rules r JOIN document_versions v ON v.id = r.version_id
                              JOIN documents d ON d.id = v.document_id
                              WHERE r.workspace_id = ? AND r.status = 'Pending Validation' AND d.authority_rank >= ?""",
                           (ws, min_authority_rank)).fetchall():
            db.update("brand_rules", r["id"], c=c, status="Approved", approved_by=user_id, approved_at=db.now(), updated_at=db.now())
            n += 1
        for f in c.execute("""SELECT f.id FROM brand_facts f JOIN document_versions v ON v.id = f.version_id
                              JOIN documents d ON d.id = v.document_id
                              WHERE f.workspace_id = ? AND f.status = 'Pending Validation' AND d.authority_rank >= ?""",
                           (ws, min_authority_rank)).fetchall():
            db.update("brand_facts", f["id"], c=c, status="Approved")
        c.execute("""UPDATE documents SET review_status = 'Approved', updated_at = ? WHERE workspace_id = ? AND status = 'active'
                     AND review_status = 'Pending review' AND authority_rank >= ?""", (db.now(), ws, min_authority_rank))
        repo.log(ws, user_id, "Bulk approval", "rule", None, f"{n} rules approved (authority ≥ {min_authority_rank})", c=c)
    return n


def edit_rule(ws, user_id, rule_id, new_text, reason, scope=None, approve=True):
    """Save a new version of a rule's wording (e.g. a RuleProbe clarification)."""
    require(user_id, MANAGER)
    new_text = (new_text or "").strip()
    if len(new_text) < 5:
        raise ValueError("Rule text is too short.")
    if not (reason or "").strip():
        raise ValueError("A reason for the change is required.")
    r = repo.get_rule(rule_id)
    ver = r["rule_version"] + 1
    scope = scope or r["scope"]
    with db.transaction() as c:
        fields = dict(text=new_text, scope=scope, rule_version=ver, constraints_json=json.dumps(kx.parse_constraints(new_text)),
                      clarity="Untested", divergence=None, updated_at=db.now())
        if approve:
            fields.update(status="Approved", approved_by=user_id, approved_at=db.now())
        db.update("brand_rules", rule_id, c=c, **fields)
        db.insert("rule_revisions", c=c, rule_id=rule_id, rule_version=ver, text=new_text, scope=scope, changed_by=user_id,
                  reason=reason.strip(), created_at=db.now())
        repo.log(ws, user_id, "Rule revised", "rule", rule_id, f"{r['code']} → v{ver}: {reason[:80]}", c=c)
    return ver


def add_rule(ws, user_id, text, category, scope="All content", reason="", approve=False):
    """A Brand Manager adds a rule by hand. It has no source document, so it is shown as 'added manually'; it starts
    Pending review unless the Brand Manager explicitly approves it while adding it."""
    require(user_id, MANAGER)
    text = (text or "").strip()
    if len(text) < 5:
        raise ValueError("Rule text is too short.")
    if category not in config.DISPLAY_CATEGORY:
        raise ValueError(f"Unknown category {category}")
    if not (reason or "").strip():
        raise ValueError("Say why this rule is being added (for example, the decision or meeting it comes from).")
    who = repo.user(user_id)["name"]
    with db.transaction() as c:
        code = repo.next_rule_code(ws, c)
        fields = dict(workspace_id=ws, code=code, text=text, category=category, scope=scope or "All content", rule_version=1,
                      version_id=None, passage_id=None, status="Approved" if approve else "Pending Validation",
                      constraints_json=json.dumps(kx.parse_constraints(text)), clarity="Untested",
                      extracted_by=f"manual · {who}", created_at=db.now(), updated_at=db.now())
        if approve:
            fields.update(approved_by=user_id, approved_at=db.now())
        rid = db.insert("brand_rules", c=c, **fields)
        db.insert("rule_revisions", c=c, rule_id=rid, rule_version=1, text=text, scope=fields["scope"], changed_by=user_id,
                  reason=f"Added manually: {reason.strip()}", created_at=db.now())
        repo.log(ws, user_id, "Rule added", "rule", rid, f"{code}: {text[:80]}", c=c)
    return rid


def set_fact_status(ws, user_id, fact_id, status):
    require(user_id, MANAGER)
    if status not in ("Approved", "Rejected", "Superseded", "Archived", "Pending Validation"):
        raise ValueError(f"Unknown status {status}")
    with db.transaction() as c:
        db.update("brand_facts", fact_id, c=c, status=status)
        repo.log(ws, user_id, f"Fact {status.lower()}", "fact", fact_id, "", c=c)


def save_terms(ws, user_id, rows):
    """Replace the term list. rows: [{'term','kind','replacement'}]."""
    require(user_id, MANAGER)
    clean = [r for r in rows if str(r.get("term", "")).strip()]
    with db.transaction() as c:
        c.execute("DELETE FROM terms WHERE workspace_id = ?", (ws,))
        seen = set()
        for r in clean:
            key = (r["term"].strip().lower(), r.get("kind") or "prohibited")
            if key in seen:
                continue
            seen.add(key)
            db.insert("terms", c=c, workspace_id=ws, term=r["term"].strip(), kind=key[1],
                      replacement=str(r.get("replacement") or "").strip(), created_at=db.now())
        repo.log(ws, user_id, "Term list updated", "terms", None, f"{len(seen)} terms", c=c)
    return len(seen)


def archive_document(ws, user_id, doc_id):
    require(user_id, MANAGER)
    with db.transaction() as c:
        db.update("documents", doc_id, c=c, status="archived", review_status="Archived", updated_at=db.now())
        vids = [r["id"] for r in c.execute("SELECT id FROM document_versions WHERE document_id = ?", (doc_id,))]
        for vid in vids:
            c.execute("UPDATE brand_rules SET status = 'Archived', updated_at = ? WHERE version_id = ?", (db.now(), vid))
            c.execute("UPDATE brand_facts SET status = 'Archived' WHERE version_id = ?", (vid,))
        repo.log(ws, user_id, "Archived document", "document", doc_id, "", c=c)


def delete_document(ws, user_id, doc_id):
    """Permanently delete a document, its versions, passages, rules, facts and any conflicts that referenced them."""
    require(user_id, MANAGER)
    doc = db.get("documents", doc_id)
    with db.transaction() as c:
        c.execute("""DELETE FROM source_conflicts WHERE id IN (
                       SELECT s.conflict_id FROM conflict_sides s
                       LEFT JOIN brand_rules r ON r.id = s.rule_id LEFT JOIN brand_facts f ON f.id = s.fact_id
                       LEFT JOIN document_versions v ON v.id = coalesce(r.version_id, f.version_id)
                       WHERE v.document_id = ?)""", (doc_id,))
        c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))  # cascades to versions, passages, rules, facts
        repo.log(ws, user_id, "Deleted document", "document", doc_id, doc["title"] if doc else "", c=c)


DOC_REVIEW = ("Pending review", "Approved", "Rejected", "Archived")


def set_document_status(ws, user_id, doc_id, status, note=""):
    """Record whether a document is accepted as a source. Approving a document does NOT approve its extracted rules —
    each rule is still reviewed. Rejecting one rejects its rules and facts that are still pending."""
    require(user_id, MANAGER)
    if status not in DOC_REVIEW:
        raise ValueError(f"Unknown document status {status}.")
    if status == "Archived":
        archive_document(ws, user_id, doc_id)
        return
    if status == "Rejected" and not (note or "").strip():
        raise ValueError("Please give a reason for rejecting this document.")
    with db.transaction() as c:
        db.update("documents", doc_id, c=c, review_status=status, review_note=(note or "").strip() or None, updated_at=db.now())
        if status == "Rejected":
            for vid in [r["id"] for r in c.execute("SELECT id FROM document_versions WHERE document_id = ?", (doc_id,))]:
                c.execute("UPDATE brand_rules SET status = 'Rejected', updated_at = ? WHERE version_id = ? AND status = 'Pending Validation'",
                          (db.now(), vid))
                c.execute("UPDATE brand_facts SET status = 'Rejected' WHERE version_id = ? AND status = 'Pending Validation'", (vid,))
        doc = db.get("documents", doc_id)
        repo.log(ws, user_id, f"Document {status.lower()}", "document", doc_id, (note or doc["title"])[:100], c=c)


def compare_versions(doc_id):
    """Rules extracted from the previous vs the current version of a document: added, removed, unchanged."""
    vers = db.fetch_all("SELECT * FROM document_versions WHERE document_id = ? ORDER BY id", (doc_id,))
    if len(vers) < 2:
        return None
    prev, cur = vers[-2], vers[-1]
    rules = lambda vid: {r["text"].strip(): r for r in db.fetch_all("SELECT * FROM brand_rules WHERE version_id = ?", (vid,))}  # noqa: E731
    a, b = rules(prev["id"]), rules(cur["id"])
    return {"previous": prev, "current": cur, "added": [b[t] for t in b if t not in a],
            "removed": [a[t] for t in a if t not in b], "unchanged": [b[t] for t in b if t in a]}
