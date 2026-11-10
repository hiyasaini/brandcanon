"""Notifications and the activity timeline — both derived from stored records, never invented.

Each item says where to go: `page` is a page key (overview, constitution, ruleprobe, auditor, decisions, governance,
settings) and `state` is the session-state the page reads to open the right record or tab.
"""
from database import db, repositories as repo

HIDDEN = {"Signed in", "Failed sign-in", "Changed password", "Activated account", "Reset a password"}


def _label(a):
    """Plain-language label and tone for an activity row."""
    act, detail = a["action"], a["detail"] or ""
    if act == "Uploaded document":
        return "Document uploaded and rules extracted", "terracotta"
    if act in ("Rule approved", "Bulk approval"):
        return "Rule approved", "olive"
    if act == "Ran RuleProbe":
        return ("Rule ambiguity identified", "amber") if "Ambiguous" in detail else (
            ("Rule contradiction identified", "red") if "Contradictory" in detail else ("Rule tested", "neutral"))
    if act == "Conflicts detected":
        return "Source conflict recorded", "red"
    if act in ("Resolved source conflict", "Resolved rule conflict"):
        return "Source conflict resolved", "olive"
    if act in ("Audited content", "New revision"):
        return "Content audit completed", "terracotta"
    if act.startswith("Decision:") or act in ("Overrode earlier decision", "Overrode finding"):
        return "Review decision saved", "olive"
    if act in ("Resolved RuleProbe finding", "Investigation updated"):
        return "Investigation updated", "olive"
    return act, "neutral"


def _target(a):
    et, eid = a["entity_type"], a["entity_id"]
    if et == "document" and eid:
        return "constitution", {"con_doc": eid, "con_tab": "Library"}
    if et == "rule":
        return "constitution", ({"con_rule": eid} if eid else {})
    if et == "rule_test" and eid:
        t = db.get("rule_tests", eid)
        return ("ruleprobe", {"probe_rule": t["rule_id"]}) if t else ("ruleprobe", {})
    if et == "conflict":
        return "ruleprobe", {"probe_tab": "Conflicts"}
    if et == "submission" and eid:
        return ("decisions", {"dm_sub": eid}) if a["action"].startswith("Decision") else ("auditor", {"aud_sub": eid})
    if et == "decision" and eid:
        return "decisions", {"dm_decision": eid, "dm_tab": "Decision history"}
    if et == "finding":
        return "decisions", {"dm_tab": "Decision history"}
    return None, {}


def timeline(ws, limit=8):
    rows = [a for a in repo.recent_activity(ws, limit * 4) if a["action"] not in HIDDEN][:limit]
    out = []
    for a in rows:
        label, tone = _label(a)
        page, state = _target(a)
        out.append({"id": a["id"], "label": label, "tone": tone, "detail": a["detail"] or "", "who": a["user_name"] or "System",
                    "at": a["created_at"], "page": page, "state": state})
    return out


def for_user(ws, user):
    """What needs this person's attention right now, by role."""
    items, role = [], user["role"]
    if role == "Brand Manager":
        docs = [d for d in repo.list_documents(ws) if (d.get("review_status") or "Pending review") == "Pending review"]
        if docs:
            items.append({"title": f"{len(docs)} document(s) awaiting review", "detail": "Approve or reject them as sources.",
                          "page": "constitution", "state": {"con_tab": "Library"}, "tone": "amber"})
        pending = repo.list_rules(ws, ("Pending Validation",))
        if pending:
            items.append({"title": f"{len(pending)} extracted rule(s) awaiting review", "detail": "Nothing is official until approved.",
                          "page": "constitution", "state": {"con_status": "Needs review"}, "tone": "amber"})
        from modules import rule_probe
        for x in [x for x in rule_probe.open_findings(ws) if x["test"]["investigation_state"] != "in_review"][:4]:
            items.append({"title": f"{x['rule']['code']}: potential {x['test']['classification'].lower()}",
                          "detail": "Not yet reviewed. " + x["rule"]["text"][:80],
                          "page": "ruleprobe", "state": {"probe_rule": x["rule"]["id"]}, "tone": "amber"})
        for c in repo.list_conflicts(ws, "open")[:4]:
            items.append({"title": f"Conflict: {c['title']}", "detail": (c["explanation"] or "")[:90],
                          "page": "ruleprobe", "state": {"probe_tab": "Conflicts"}, "tone": "red"})
        for s in repo.list_submissions(ws, ("Escalated",)):
            items.append({"title": f"Escalated: {s['title']}", "detail": "A reviewer needs a brand decision.",
                          "page": "decisions", "state": {"dm_sub": s["id"]}, "tone": "red"})
    if role in ("Brand Manager", "Reviewer"):
        for t in in_review_investigations(ws):
            items.append({"title": f"Investigation sent for review: {t['code']}", "detail": (t["notes"] or t["issue"])[:90],
                          "page": "ruleprobe", "state": {"probe_rule": t["rule_id"]}, "tone": "amber"})
    if role == "Reviewer":
        for s in repo.list_submissions(ws, ("In review",)):
            items.append({"title": f"Review: {s['title']}", "detail": f"{s['channel']} · revision {s['latest_revision']} · {s['author_name']}",
                          "page": "decisions", "state": {"dm_sub": s["id"]}, "tone": "terracotta"})
    if role == "Creator":
        for s in repo.list_submissions(ws, ("Changes requested", "Draft"), author_id=user["id"]):
            items.append({"title": f"{s['status']}: {s['title']}", "detail": "Open it in the Content Auditor.",
                          "page": "auditor", "state": {"aud_sub": s["id"]}, "tone": "amber"})
    return items


def in_review_investigations(ws):
    cols = {r["name"] for r in db.fetch_all("PRAGMA table_info(rule_tests)")}
    if "investigation_state" not in cols:
        return []
    return db.fetch_all("""SELECT t.*, r.code FROM rule_tests t JOIN brand_rules r ON r.id = t.rule_id
                           WHERE r.workspace_id = ? AND t.investigation_state = 'in_review' ORDER BY t.id DESC""", (ws,))
