"""Submissions, revisions, persisted audit reports, finding dispositions and reviewer decisions."""
from database import db, repositories as repo
from modules import content_audit, decision_memory
from modules.access import require

REVIEW_ROLES = ("Reviewer", "Brand Manager")


def save_report(ws, user_id, revision_id, result, c=None):
    def _save(c):
        rid = db.insert("audit_reports", c=c, workspace_id=ws, revision_id=revision_id, channel=result["channel"],
                        content_type=result["content_type"], product=result["product"], engine=result["engine"],
                        overall_status=result["status"], n_high=result["counts"]["high"], n_medium=result["counts"]["medium"],
                        n_low=result["counts"]["low"], created_by=user_id, created_at=db.now())
        for i, f in enumerate(result["findings"]):
            f["id"] = db.insert("audit_findings", c=c, report_id=rid, seq=i, category=f["category"],
                                classification=f["classification"], severity=f["severity"], span_start=f.get("span_start"),
                                span_end=f.get("span_end"), quote=f.get("quote", ""), message=f["message"],
                                suggestion=f.get("suggestion") or "", rule_id=f.get("rule_id"), fact_id=f.get("fact_id"),
                                passage_id=f.get("passage_id"), evidence_text=f.get("evidence_text") or "",
                                evidence_source=f.get("evidence_source") or "", root_cause=f["root_cause"],
                                confidence=f["confidence"], engine=f.get("engine", "Deterministic"))
        return rid
    return _save(c) if c is not None else _with_tx(_save)


def _with_tx(fn):
    with db.transaction() as c:
        return fn(c)


def create_draft(ws, user_id, title, text, content_type, channel, product=None, campaign=None, alt_text="",
                 has_image=False, use_ai=True):
    if not (text or "").strip():
        raise ValueError("Content is empty.")
    result = content_audit.run(ws, text, channel, content_type, product, has_image, alt_text, use_ai)
    with db.transaction() as c:
        sid = db.insert("content_submissions", c=c, workspace_id=ws, title=(title or "Untitled").strip(),
                        content_type=content_type, channel=channel, product=result["product"], campaign=campaign or None,
                        author_id=user_id, status="Draft", created_at=db.now(), updated_at=db.now())
        rev = db.insert("content_revisions", c=c, submission_id=sid, revision_no=1, text=text, alt_text=alt_text,
                        note="First draft", created_by=user_id, created_at=db.now())
        rid = save_report(ws, user_id, rev, result, c=c)
        repo.log(ws, user_id, "Audited content", "submission", sid, f"{title}: {result['status']} ({result['engine']})", c=c)
    return sid, rev, rid


def add_revision(ws, user_id, sid, text, note, alt_text="", has_image=False, use_ai=True):
    sub = repo.get_submission(sid)
    if sub["status"] == "Approved":
        raise ValueError("This content is already approved; start a new submission to change it.")
    result = content_audit.run(ws, text, sub["channel"], sub["content_type"], sub["product"], has_image, alt_text, use_ai)
    prev = repo.revisions(sid)[-1]
    prev_rep = repo.latest_report(prev["id"])
    dismissed = {(f["quote"], f["classification"], f["category"]): f for f in (repo.findings(prev_rep["id"]) if prev_rep else [])
                 if f["disposition"] == "dismissed" and f["quote"]}
    with db.transaction() as c:
        n = c.execute("SELECT MAX(revision_no) n FROM content_revisions WHERE submission_id = ?", (sid,)).fetchone()["n"] + 1
        rev = db.insert("content_revisions", c=c, submission_id=sid, revision_no=n, text=text, alt_text=alt_text,
                        note=note or f"Revision {n}", created_by=user_id, created_at=db.now())
        rid = save_report(ws, user_id, rev, result, c=c)
        # a dismissal stands for the same issue on the same phrase in later revisions (with its original reason)
        for f in c.execute("SELECT id, quote, classification, category FROM audit_findings WHERE report_id = ?", (rid,)).fetchall():
            old = dismissed.get((f["quote"], f["classification"], f["category"]))
            if old:
                db.update("audit_findings", f["id"], c=c, disposition="dismissed", disposed_by=old["disposed_by"],
                          disposition_reason=f"{old['disposition_reason']} (dismissed on revision {prev['revision_no']})")
        status = "In review" if sub["status"] in ("In review", "Changes requested") else sub["status"]
        db.update("content_submissions", sid, c=c, status=status, updated_at=db.now())
        repo.log(ws, user_id, "New revision", "submission", sid, f"v{n}: {result['status']}", c=c)
    return rev, rid


def apply_and_revise(ws, user_id, sid, finding_rows, replacements, note="Applied suggested corrections"):
    """Accept/edit suggestions: record dispositions, create a new revision with the corrected text and re-audit it."""
    rev = repo.revisions(sid)[-1]
    findings = [dict(f) for f in finding_rows]
    new_text = content_audit.apply_suggestions(rev["text"], findings, replacements)
    for i, rep in replacements.items():
        f = findings[i]
        disp = "accepted" if rep == (f.get("suggestion") or "") else "edited"
        db.update("audit_findings", f["id"], disposition=disp, disposition_reason=None if disp == "accepted" else f"Edited to: {rep}",
                  disposed_by=user_id)
    return add_revision(ws, user_id, sid, new_text, note, rev.get("alt_text") or "")


def dismiss_finding(ws, user_id, finding_id, reason):
    if not (reason or "").strip():
        raise ValueError("Please give a reason for dismissing this finding.")
    db.update("audit_findings", finding_id, disposition="dismissed", disposition_reason=reason.strip(), disposed_by=user_id)
    repo.log(ws, user_id, "Dismissed finding", "finding", finding_id, reason[:100])


def submit(ws, user_id, sid):
    sub = repo.get_submission(sid)
    if sub["status"] not in ("Draft", "Changes requested"):
        raise ValueError(f"Cannot submit content with status {sub['status']}.")
    db.update("content_submissions", sid, status="In review", updated_at=db.now())
    repo.log(ws, user_id, "Submitted for review", "submission", sid, sub["title"])


def comment(sid, user_id, text, revision_no=None):
    if not (text or "").strip():
        raise ValueError("Comment is empty.")
    db.insert("comments", submission_id=sid, revision_no=revision_no, user_id=user_id, text=text.strip(), created_at=db.now())


def _fact_or_rule_version(f):
    if f.get("fact_id"):
        row = db.get("brand_facts", f["fact_id"])
        return row["version_id"] if row else None
    if f.get("rule_id"):
        row = db.get("brand_rules", f["rule_id"])
        return row["version_id"] if row else None
    return None


def override_finding(ws, reviewer_id, sid, finding_id, explanation):
    """A reviewer decides a finding is not an issue here. Stored as a decision (precedent), not as a rule change."""
    require(reviewer_id, *REVIEW_ROLES)
    if not (explanation or "").strip():
        raise ValueError("An explanation is required.")
    f = db.get("audit_findings", finding_id)
    sub = repo.get_submission(sid)
    rev = repo.revisions(sid)[-1]
    with db.transaction() as c:
        db.update("audit_findings", finding_id, c=c, disposition="dismissed", disposition_reason=f"Reviewer override: {explanation}",
                  disposed_by=reviewer_id)
        db.insert("decisions", c=c, workspace_id=ws, submission_id=sid, revision_id=rev["id"], finding_id=finding_id,
                  rule_id=f["rule_id"], fact_id=f["fact_id"], source_version_id=_fact_or_rule_version(f),
                  decision="Finding overridden", claim_text=f["quote"] or f["message"][:120], finding_category=f["category"],
                  explanation=explanation.strip(), channel=sub["channel"], product=sub["product"], campaign=sub["campaign"],
                  reviewer_id=reviewer_id, created_at=db.now())
        repo.log(ws, reviewer_id, "Overrode finding", "finding", finding_id, explanation[:100], c=c)


def decide(ws, reviewer_id, sid, outcome, rationale):
    """Final review outcome for the latest revision. Also stores each original issue as a precedent decision."""
    if outcome not in ("Approved", "Changes requested", "Rejected", "Escalated"):
        raise ValueError(f"Unknown outcome {outcome}")
    sub = repo.get_submission(sid)
    if sub["status"] == "Escalated":
        require(reviewer_id, "Brand Manager")
    else:
        require(reviewer_id, *REVIEW_ROLES)
    if sub["status"] not in ("In review", "Escalated"):
        raise ValueError(f"Content with status {sub['status']} is not waiting for review.")
    if not (rationale or "").strip():
        raise ValueError("A rationale is required; it becomes precedent for future reviews.")
    revs = repo.revisions(sid)
    latest, first = revs[-1], revs[0]
    first_report = repo.latest_report(first["id"])
    first_findings = repo.findings(first_report["id"]) if first_report else []
    with db.transaction() as c:
        dec_id = db.insert("decisions", c=c, workspace_id=ws, submission_id=sid, revision_id=latest["id"], decision=outcome,
                           claim_text=latest["text"][:200], explanation=rationale.strip(),
                           approved_correction=latest["text"] if outcome == "Approved" else None, channel=sub["channel"],
                           product=sub["product"], campaign=sub["campaign"], reviewer_id=reviewer_id, created_at=db.now())
        if outcome in ("Approved", "Rejected"):  # final outcomes become claim-level precedent
            for f in first_findings:
                if f["classification"] == "Verified" or (f["disposition"] == "dismissed" and "Reviewer override" in (f["disposition_reason"] or "")):
                    continue
                if c.execute("SELECT 1 FROM decisions WHERE finding_id = ?", (f["id"],)).fetchone():
                    continue
                db.insert("decisions", c=c, workspace_id=ws, submission_id=sid, revision_id=latest["id"], finding_id=f["id"],
                          rule_id=f["rule_id"], fact_id=f["fact_id"], source_version_id=_fact_or_rule_version(f),
                          decision="Finding upheld", claim_text=f["quote"] or f["message"][:120], finding_category=f["category"],
                          explanation=f"{f['message']} Reviewer: {rationale.strip()}",
                          approved_correction=f["suggestion"] or None, channel=sub["channel"], product=sub["product"],
                          campaign=sub["campaign"], reviewer_id=reviewer_id, created_at=db.now())
        db.insert("approvals", c=c, submission_id=sid, revision_id=latest["id"], outcome=outcome, rationale=rationale.strip(),
                  reviewer_id=reviewer_id, decision_id=dec_id, created_at=db.now())
        db.update("content_submissions", sid, c=c, status=outcome, updated_at=db.now())
        repo.log(ws, reviewer_id, f"Decision: {outcome}", "submission", sid, f"v{latest['revision_no']}: {rationale[:80]}", c=c)
    return dec_id


def report_with_context(ws, revision_id, exclude_submission=None):
    """Latest report for a revision plus its findings and precedents (for display)."""
    rep = repo.latest_report(revision_id)
    if not rep:
        return None, []
    fs = repo.findings(rep["id"])
    decision_memory.attach(ws, fs, rep["product"], rep["channel"], exclude_submission=exclude_submission)
    return rep, fs
