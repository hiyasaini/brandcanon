"""Upload pipeline: validate → parse → screen → version → store passages → extract → detect conflicts."""
import re
from pathlib import Path

import config
from database import db, repositories as repo
from modules import document_parser, knowledge_extraction as kx
from modules.access import require
from services import file_service


class IngestionError(ValueError):
    pass


def guess_authority(name: str) -> str:
    n = name.lower()
    if "spec" in n:
        return "Official Product Specification"
    if "guideline" in n or "brand book" in n or "style guide" in n:
        return "Official Brand Guideline"
    if "policy" in n:
        return "Approved Policy"
    if "presentation" in n or "deck" in n or "pitch" in n:
        return "Older Marketing Presentation"
    if "campaign" in n or "brief" in n:
        return "Approved Campaign Document"
    return "Informal Note"


def guess_version(text: str):
    v = re.search(r"\bversion\s*([0-9]+(?:\.[0-9]+)*)", text, re.I)
    d = re.search(r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})", text)
    return (v.group(1) if v else None), (d.group(1) if d else None)


def title_from(name):
    return Path(name).stem.replace("_", " ").strip()


def ingest(ws, user_id, name, data, authority=None, title=None, use_ai=True):
    """Store a new document (or a new version of an existing one) and extract candidate knowledge.

    Returns a summary dict. Raises file_service.FileRejected / document_parser.ParseError for bad input.
    """
    require(user_id, "Brand Manager")
    ext = file_service.validate_upload(name, data)
    pages = document_parser.parse(ext, data)
    full = "\n".join(t for _, t in pages)
    if not full.strip():
        status = "empty"
    else:
        status = "extracted"
    flags = file_service.injection_hits(full)
    version_label, effective = guess_version(full)
    title = title or title_from(name)
    authority = authority or guess_authority(name)
    rank = config.AUTHORITY_LEVELS.get(authority, 0)

    passages, rules, facts, terms, engine, ai_error = (kx.extract(pages, use_ai=use_ai) if status == "extracted"
                                                       else ([], [], [], [], "none", None))

    with db.transaction() as c:
        doc = c.execute("SELECT * FROM documents WHERE workspace_id = ? AND title = ?", (ws, title)).fetchone()
        superseded = 0
        if doc:
            doc_id = doc["id"]
            c.execute("UPDATE documents SET authority_level = ?, authority_rank = ?, status = 'active', review_status = 'Pending review', updated_at = ? WHERE id = ?",
                      (authority, rank, db.now(), doc_id))
            old = [r["id"] for r in c.execute("SELECT id FROM document_versions WHERE document_id = ? AND is_current = 1", (doc_id,))]
            for vid in old:
                c.execute("UPDATE document_versions SET is_current = 0 WHERE id = ?", (vid,))
                superseded += c.execute("UPDATE brand_rules SET status = 'Archived', updated_at = ? WHERE version_id = ? AND status != 'Archived'",
                                        (db.now(), vid)).rowcount
                c.execute("UPDATE brand_facts SET status = 'Superseded' WHERE version_id = ? AND status NOT IN ('Rejected','Archived')", (vid,))
            n_versions = c.execute("SELECT COUNT(*) n FROM document_versions WHERE document_id = ?", (doc_id,)).fetchone()["n"]
        else:
            doc_id = db.insert("documents", c=c, workspace_id=ws, title=title, authority_level=authority, authority_rank=rank,
                               status="active", created_at=db.now(), updated_at=db.now())
            n_versions = 0
        vid = db.insert("document_versions", c=c, document_id=doc_id, version_label=version_label or f"upload {n_versions + 1}",
                        file_name=name, file_type=ext.lstrip("."),
                        file_size=len(data or b""), sha256=file_service.sha256(data),
                        effective_date=effective, page_count=len(pages), extraction_status=status, extraction_engine=engine,
                        injection_flags=len(flags), is_current=1, uploaded_by=user_id, uploaded_at=db.now())
        pid = {}
        for p in passages:
            pid[p["idx"]] = db.insert("passages", c=c, version_id=vid, location=p["location"], seq=p["idx"], text=p["text"])
        rule_ids = {}
        for r in rules:
            code = repo.next_rule_code(ws, c)
            rid = db.insert("brand_rules", c=c, workspace_id=ws, code=code, text=r["text"], category=r["category"],
                            scope=r["scope"], rule_version=1, version_id=vid, passage_id=pid.get(r["idx"]),
                            status="Pending Validation", constraints_json=_json(kx.parse_constraints(r["text"])),
                            clarity="Untested", extracted_by=engine, created_at=db.now(), updated_at=db.now())
            db.insert("rule_revisions", c=c, rule_id=rid, rule_version=1, text=r["text"], scope=r["scope"],
                      changed_by=user_id, reason=f"Extracted from {title} ({engine})", created_at=db.now())
            rule_ids[r["idx"]] = rid
        for f in facts:
            db.insert("brand_facts", c=c, workspace_id=ws, product=f["product"], attribute=f["attribute"], value=f["value"],
                      unit=f["unit"], qualifier=f["qualifier"], raw_text=f["text"], version_id=vid,
                      passage_id=pid.get(f["idx"]), status="Pending Validation", created_at=db.now())
        n_terms = 0
        for t in terms:
            if c.execute("SELECT 1 FROM terms WHERE workspace_id = ? AND lower(term) = lower(?) AND kind = ?",
                         (ws, t["term"], t["kind"])).fetchone():
                continue
            db.insert("terms", c=c, workspace_id=ws, term=t["term"], kind=t["kind"], replacement=t["replacement"],
                      rule_id=rule_ids.get(t["idx"]), created_at=db.now())
            n_terms += 1
        repo.log(ws, user_id, "Uploaded document", "document", doc_id,
                 f"{title} v{version_label or n_versions + 1}: {len(rules)} rules, {len(facts)} facts ({engine})", c=c)

    from modules import conflict_detection
    new_conflicts = conflict_detection.detect(ws, user_id)
    return {"document_id": doc_id, "version_id": vid, "title": title, "status": status, "engine": engine, "ai_error": ai_error,
            "rules": len(rules), "facts": len(facts), "terms": n_terms, "passages": len(passages),
            "superseded_rules": superseded, "injection_flags": flags, "new_conflicts": new_conflicts,
            "is_new_version": n_versions > 0}


def _json(d):
    import json
    return json.dumps(d)
