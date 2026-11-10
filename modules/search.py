"""Global search across the workspace's stored records (rules, facts, documents, findings, decisions, content).

Plain parameterised LIKE queries; results carry the screen and record to open. Nothing is ranked by a model.
"""
from database import db


def search(ws, text, limit=12):
    t = (text or "").strip()
    if len(t) < 2:
        return {}
    like = f"%{t.lower()}%"
    out = {}
    out["Brand rules"] = [
        dict(title=f"{r['code']} · {r['text'][:110]}", sub=f"{r['status']} · {r['category']}", page="constitution",
             state={"con_rule": r["id"]})
        for r in db.fetch_all("SELECT id, code, text, status, category FROM brand_rules WHERE workspace_id = ? AND "
                              "(lower(text) LIKE ? OR lower(code) LIKE ? OR lower(category) LIKE ?) ORDER BY code LIMIT ?",
                              (ws, like, like, like, limit))]
    out["Documents"] = [
        dict(title=d["title"], sub=f"{d['authority_level']} · {d['review_status']}", page="constitution",
             state={"con_doc": d["id"]})
        for d in db.fetch_all("SELECT id, title, authority_level, review_status FROM documents WHERE workspace_id = ? AND "
                              "lower(title) LIKE ? ORDER BY title LIMIT ?", (ws, like, limit))]
    out["Document passages"] = [
        dict(title=p["text"][:140], sub=f"{p['title']} · {p['location']}", page="constitution", state={"con_doc": p["doc_id"]})
        for p in db.fetch_all("""SELECT p.text, p.location, d.title, d.id doc_id FROM passages p
                                 JOIN document_versions v ON v.id = p.version_id AND v.is_current = 1
                                 JOIN documents d ON d.id = v.document_id
                                 WHERE d.workspace_id = ? AND lower(p.text) LIKE ? ORDER BY d.title, p.seq LIMIT ?""",
                              (ws, like, limit))]
    out["Product facts"] = [
        dict(title=f["raw_text"][:140], sub=f"{f['product']} · {f['attribute']} · {f['status']}", page="constitution",
             state={"con_view": "Product facts"})
        for f in db.fetch_all("SELECT raw_text, product, attribute, status FROM brand_facts WHERE workspace_id = ? AND "
                              "(lower(raw_text) LIKE ? OR lower(product) LIKE ? OR lower(attribute) LIKE ?) LIMIT ?",
                              (ws, like, like, like, limit))]
    out["Audit findings"] = [
        dict(title=f"“{f['quote'] or 'whole text'}” · {f['classification']}", sub=f"{f['title']} · {f['category']}",
             page="auditor", state={"aud_sub": f["submission_id"]})
        for f in db.fetch_all("""SELECT f.quote, f.classification, f.category, s.title, s.id submission_id
                                 FROM audit_findings f JOIN audit_reports a ON a.id = f.report_id
                                 JOIN content_revisions r ON r.id = a.revision_id JOIN content_submissions s ON s.id = r.submission_id
                                 WHERE a.workspace_id = ? AND f.classification != 'Verified'
                                 AND (lower(f.quote) LIKE ? OR lower(f.message) LIKE ?) ORDER BY f.id DESC LIMIT ?""",
                              (ws, like, like, limit))]
    out["Decisions"] = [
        dict(title=f"{d['decision']} · {(d['claim_text'] or d['explanation'])[:110]}", sub=f"{d['created_at'][:10]}",
             page="decisions", state={"dm_decision": d["id"]})
        for d in db.fetch_all("SELECT id, decision, claim_text, explanation, created_at FROM decisions WHERE workspace_id = ? "
                              "AND (lower(claim_text) LIKE ? OR lower(explanation) LIKE ?) ORDER BY id DESC LIMIT ?",
                              (ws, like, like, limit))]
    out["Content"] = [
        dict(title=s["title"], sub=f"{s['status']} · {s['channel'] or ''}", page="auditor", state={"aud_sub": s["id"]})
        for s in db.fetch_all("""SELECT DISTINCT s.id, s.title, s.status, s.channel FROM content_submissions s
                                 JOIN content_revisions r ON r.submission_id = s.id WHERE s.workspace_id = ? AND
                                 (lower(s.title) LIKE ? OR lower(r.text) LIKE ?) ORDER BY s.id DESC LIMIT ?""",
                              (ws, like, like, limit))]
    return {k: v for k, v in out.items() if v}
