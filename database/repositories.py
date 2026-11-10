"""Named, parameterised queries. Business modules use these instead of writing SQL inline."""
import json

from . import db

# ---------------------------------------------------------------- workspaces & users


def get_or_create_workspace(name, is_demo=False):
    row = db.fetch_one("SELECT * FROM workspaces WHERE name = ?", (name,))
    if row:
        return row["id"]
    return db.insert("workspaces", name=name, is_demo=int(is_demo), created_at=db.now())


def list_workspaces():
    return db.fetch_all("SELECT * FROM workspaces ORDER BY is_demo DESC, id")


def get_or_create_user(ws, name, role):
    row = db.fetch_one("SELECT * FROM users WHERE workspace_id = ? AND name = ? AND role = ?", (ws, name, role))
    if row:
        return row["id"]
    return db.insert("users", workspace_id=ws, name=name, role=role, created_at=db.now())


def users(ws):
    return db.fetch_all("SELECT * FROM users WHERE workspace_id = ? ORDER BY role, name", (ws,))


def user(uid):
    return db.get("users", uid) if uid else None


def log(ws, user_id, action, entity_type=None, entity_id=None, detail="", c=None):
    db.insert("activity_log", c=c, workspace_id=ws, user_id=user_id, action=action, entity_type=entity_type,
              entity_id=entity_id, detail=(detail or "")[:300], created_at=db.now())


def recent_activity(ws, limit=8):
    return db.fetch_all("""SELECT a.*, u.name user_name, u.role user_role FROM activity_log a
                           LEFT JOIN users u ON u.id = a.user_id WHERE a.workspace_id = ?
                           ORDER BY a.id DESC LIMIT ?""", (ws, limit))


# ---------------------------------------------------------------- documents

DOC_SELECT = """SELECT d.*, v.id version_id, v.version_label, v.file_name, v.file_type, v.file_size, v.page_count,
                v.extraction_status, v.extraction_engine, v.effective_date, v.uploaded_at, v.injection_flags, v.source_url
                FROM documents d LEFT JOIN document_versions v ON v.document_id = d.id AND v.is_current = 1"""


def list_documents(ws, include_archived=False):
    q = DOC_SELECT + " WHERE d.workspace_id = ?" + ("" if include_archived else " AND d.status = 'active'") + " ORDER BY d.id"
    return db.fetch_all(q, (ws,))


def find_document(ws, title):
    return db.fetch_one("SELECT * FROM documents WHERE workspace_id = ? AND title = ?", (ws, title))


def document_versions(doc_id):
    return db.fetch_all("SELECT * FROM document_versions WHERE document_id = ? ORDER BY id DESC", (doc_id,))


def passages(ws, current_only=True):
    q = """SELECT p.*, v.version_label, v.file_name, v.is_current, d.title doc_title, d.id document_id,
                  d.authority_level, d.authority_rank
           FROM passages p JOIN document_versions v ON v.id = p.version_id JOIN documents d ON d.id = v.document_id
           WHERE d.workspace_id = ? AND d.status = 'active'""" + (" AND v.is_current = 1" if current_only else "")
    return db.fetch_all(q + " ORDER BY p.id", (ws,))


def passage(pid):
    return db.fetch_one("""SELECT p.*, v.version_label, v.file_name, v.is_current, d.title doc_title, d.authority_level,
                                  d.authority_rank FROM passages p JOIN document_versions v ON v.id = p.version_id
                           JOIN documents d ON d.id = v.document_id WHERE p.id = ?""", (pid,))


# ---------------------------------------------------------------- rules, facts, terms

RULE_SELECT = """SELECT r.*, d.id document_id, v.version_label doc_version, v.file_name, v.is_current doc_current, d.title doc_title,
                 d.authority_level, d.authority_rank, p.location, p.text source_text, u.name approved_by_name
                 FROM brand_rules r LEFT JOIN document_versions v ON v.id = r.version_id
                 LEFT JOIN documents d ON d.id = v.document_id LEFT JOIN passages p ON p.id = r.passage_id
                 LEFT JOIN users u ON u.id = r.approved_by"""


def _rule(row):
    if row:
        row["constraints"] = json.loads(row.get("constraints_json") or "{}")
    return row


def list_rules(ws, statuses=None):
    q, params = RULE_SELECT + " WHERE r.workspace_id = ?", [ws]
    if statuses:
        q += f" AND r.status IN ({','.join('?' * len(statuses))})"
        params += list(statuses)
    return [_rule(r) for r in db.fetch_all(q + " ORDER BY r.id", params)]


def get_rule(rid):
    return _rule(db.fetch_one(RULE_SELECT + " WHERE r.id = ?", (rid,)))


def next_rule_code(ws, c=None):
    row = (c.execute("SELECT COUNT(*) n FROM brand_rules WHERE workspace_id = ?", (ws,)).fetchone() if c
           else db.fetch_one("SELECT COUNT(*) n FROM brand_rules WHERE workspace_id = ?", (ws,)))
    return f"R{row['n'] + 1:03d}"


def rule_revisions(rid):
    return db.fetch_all("""SELECT rr.*, u.name changed_by_name FROM rule_revisions rr LEFT JOIN users u ON u.id = rr.changed_by
                           WHERE rr.rule_id = ? ORDER BY rr.id DESC""", (rid,))


FACT_SELECT = """SELECT f.*, v.version_label doc_version, v.file_name, v.is_current doc_current, d.title doc_title,
                 d.authority_level, d.authority_rank, p.location, p.text source_text
                 FROM brand_facts f LEFT JOIN document_versions v ON v.id = f.version_id
                 LEFT JOIN documents d ON d.id = v.document_id LEFT JOIN passages p ON p.id = f.passage_id"""


def list_facts(ws, statuses=None):
    q, params = FACT_SELECT + " WHERE f.workspace_id = ?", [ws]
    if statuses:
        q += f" AND f.status IN ({','.join('?' * len(statuses))})"
        params += list(statuses)
    return db.fetch_all(q + " ORDER BY f.product, f.attribute, d.authority_rank DESC", params)


def get_fact(fid):
    return db.fetch_one(FACT_SELECT + " WHERE f.id = ?", (fid,))


def products(ws):
    return [r["product"] for r in db.fetch_all(
        "SELECT DISTINCT product FROM brand_facts WHERE workspace_id = ? AND status NOT IN ('Rejected','Archived') ORDER BY product", (ws,))]


def list_terms(ws, kind=None):
    if kind:
        return db.fetch_all("SELECT * FROM terms WHERE workspace_id = ? AND kind = ? ORDER BY term", (ws, kind))
    return db.fetch_all("SELECT * FROM terms WHERE workspace_id = ? ORDER BY kind, term", (ws,))


# ---------------------------------------------------------------- RuleProbe


def tests_for_rule(rid):
    return db.fetch_all("""SELECT t.*, u.name resolved_by_name, ru.name run_by_name FROM rule_tests t
                           LEFT JOIN users u ON u.id = t.resolved_by LEFT JOIN users ru ON ru.id = t.run_by
                           WHERE t.rule_id = ? ORDER BY t.id DESC""", (rid,))


def latest_test(rid):
    rows = tests_for_rule(rid)
    return rows[0] if rows else None


def test_cases(tid):
    return db.fetch_all("SELECT * FROM rule_test_cases WHERE test_id = ? ORDER BY seq", (tid,))


def all_tests(ws):
    return db.fetch_all("""SELECT t.*, r.code, r.text rule_text FROM rule_tests t JOIN brand_rules r ON r.id = t.rule_id
                           WHERE r.workspace_id = ? ORDER BY t.id""", (ws,))


def list_conflicts(ws, status=None):
    q, params = "SELECT * FROM source_conflicts WHERE workspace_id = ?", [ws]
    if status:
        q += " AND status = ?"
        params.append(status)
    return db.fetch_all(q + " ORDER BY id", params)


def conflict_sides(cid):
    sides = []
    for s in db.fetch_all("SELECT * FROM conflict_sides WHERE conflict_id = ? ORDER BY id", (cid,)):
        if s["rule_id"]:
            sides.append({"type": "rule", **get_rule(s["rule_id"])})
        else:
            sides.append({"type": "fact", **get_fact(s["fact_id"])})
    return sides


def open_conflicts_for_rule(rid):
    return db.fetch_all("""SELECT c.* FROM source_conflicts c JOIN conflict_sides s ON s.conflict_id = c.id
                           WHERE s.rule_id = ? AND c.status = 'open'""", (rid,))


def open_conflicts_for_fact(fid):
    return db.fetch_all("""SELECT c.* FROM source_conflicts c JOIN conflict_sides s ON s.conflict_id = c.id
                           WHERE s.fact_id = ? AND c.status = 'open'""", (fid,))


# ---------------------------------------------------------------- content


SUB_SELECT = """SELECT s.*, u.name author_name, u.role author_role,
                (SELECT MAX(revision_no) FROM content_revisions WHERE submission_id = s.id) latest_revision
                FROM content_submissions s LEFT JOIN users u ON u.id = s.author_id"""


def list_submissions(ws, statuses=None, author_id=None):
    q, params = SUB_SELECT + " WHERE s.workspace_id = ?", [ws]
    if statuses:
        q += f" AND s.status IN ({','.join('?' * len(statuses))})"
        params += list(statuses)
    if author_id:
        q += " AND s.author_id = ?"
        params.append(author_id)
    return db.fetch_all(q + " ORDER BY s.updated_at DESC, s.id DESC", params)


def get_submission(sid):
    return db.fetch_one(SUB_SELECT + " WHERE s.id = ?", (sid,))


def revisions(sid):
    return db.fetch_all("""SELECT r.*, u.name created_by_name FROM content_revisions r LEFT JOIN users u ON u.id = r.created_by
                           WHERE r.submission_id = ? ORDER BY r.revision_no""", (sid,))


def latest_report(revision_id):
    return db.fetch_one("SELECT * FROM audit_reports WHERE revision_id = ? ORDER BY id DESC LIMIT 1", (revision_id,))


def findings(report_id):
    return db.fetch_all("""SELECT f.*, r.code rule_code, r.rule_version, u.name disposed_by_name FROM audit_findings f
                           LEFT JOIN brand_rules r ON r.id = f.rule_id LEFT JOIN users u ON u.id = f.disposed_by
                           WHERE f.report_id = ? ORDER BY f.seq""", (report_id,))


def comments(sid):
    return db.fetch_all("""SELECT c.*, u.name user_name, u.role user_role FROM comments c LEFT JOIN users u ON u.id = c.user_id
                           WHERE c.submission_id = ? ORDER BY c.id""", (sid,))


def approvals(sid):
    return db.fetch_all("""SELECT a.*, u.name reviewer_name, cr.revision_no FROM approvals a
                           JOIN users u ON u.id = a.reviewer_id JOIN content_revisions cr ON cr.id = a.revision_id
                           WHERE a.submission_id = ? ORDER BY a.id""", (sid,))


DEC_SELECT = """SELECT d.*, u.name reviewer_name, s.title submission_title, r.code rule_code, v.version_label source_version,
                v.is_current source_current, doc.title source_title
                FROM decisions d LEFT JOIN users u ON u.id = d.reviewer_id
                LEFT JOIN content_submissions s ON s.id = d.submission_id LEFT JOIN brand_rules r ON r.id = d.rule_id
                LEFT JOIN document_versions v ON v.id = d.source_version_id LEFT JOIN documents doc ON doc.id = v.document_id"""


def list_decisions(ws, search=None):
    q, params = DEC_SELECT + " WHERE d.workspace_id = ?", [ws]
    if search:
        like = f"%{search.lower()}%"
        q += """ AND (lower(d.claim_text) LIKE ? OR lower(d.explanation) LIKE ? OR lower(coalesce(s.title,'')) LIKE ?
                 OR lower(coalesce(d.product,'')) LIKE ? OR lower(coalesce(r.code,'')) LIKE ?)"""
        params += [like] * 5
    return db.fetch_all(q + " ORDER BY d.id DESC", params)


def findings_for_analytics(ws, date_from=None, date_to=None, channel=None):
    q = """SELECT f.*, a.channel, a.product, a.created_at report_at, cr.revision_no, s.id submission_id, s.title,
                  s.status submission_status, r.code rule_code
           FROM audit_findings f JOIN audit_reports a ON a.id = f.report_id
           JOIN content_revisions cr ON cr.id = a.revision_id JOIN content_submissions s ON s.id = cr.submission_id
           LEFT JOIN brand_rules r ON r.id = f.rule_id WHERE a.workspace_id = ?"""
    params = [ws]
    if date_from:
        q += " AND a.created_at >= ?"
        params.append(date_from)
    if date_to:
        q += " AND a.created_at <= ?"
        params.append(date_to + "T23:59:59")
    if channel and channel != "All channels":
        q += " AND a.channel = ?"
        params.append(channel)
    return db.fetch_all(q + " ORDER BY a.created_at", params)


# ---------------------------------------------------------------- UI read helpers (v3)
def passages_at(version_id, location):
    """Every stored passage on the same page/section of a document version (for 'View source')."""
    return db.fetch_all("SELECT * FROM passages WHERE version_id = ? AND location = ? ORDER BY seq", (version_id, location))


def doc_pages(version_id):
    """Page / section labels of a stored document version, in reading order."""
    return [x["location"] for x in db.fetch_all("SELECT location, MIN(seq) s FROM passages WHERE version_id = ? "
                                                "GROUP BY location ORDER BY s", (version_id,))]


def source_page(passage_id):
    """The stored page a cited passage sits on: document, version, page/section and every passage on it, in order."""
    p = db.fetch_one("SELECT p.*, v.version_label, v.file_name, v.page_count, d.title doc_title, d.authority_level, "
                     "d.authority_rank FROM passages p JOIN document_versions v ON v.id = p.version_id "
                     "JOIN documents d ON d.id = v.document_id WHERE p.id = ?", (passage_id,))
    if not p:
        return None
    return {**p, "passages": passages_at(p["version_id"], p["location"])}


def rule_links(rule_id):
    """How far a rule reaches downstream: tests, audit findings and stored decisions that reference it."""
    one = lambda sql: db.fetch_one(sql, (rule_id,))["n"]  # noqa: E731
    return {"tests": one("SELECT COUNT(*) n FROM rule_tests WHERE rule_id = ?"),
            "findings": one("SELECT COUNT(*) n FROM audit_findings WHERE rule_id = ? AND classification != 'Verified'"),
            "decisions": one("SELECT COUNT(*) n FROM decisions WHERE rule_id = ?")}


def finding(fid):
    return db.fetch_one("""SELECT f.*, r.code rule_code, r.rule_version FROM audit_findings f
                           LEFT JOIN brand_rules r ON r.id = f.rule_id WHERE f.id = ?""", (fid,)) if fid else None


def decisions_for_submission(sid):
    return db.fetch_all(DEC_SELECT + " WHERE d.submission_id = ? ORDER BY d.id", (sid,))
