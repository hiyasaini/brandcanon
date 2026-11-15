"""Detect contradictions between rules, between product facts, and missing guidance (coverage gaps).

Conflicts are recorded for human resolution; BrandCanon never silently picks a winner.
"""
from itertools import combinations

import config
from database import db, repositories as repo
from modules import ambiguity_detection as amb
from modules import text_features as tf
from modules.access import require

LIVE = ("Pending Validation", "Approved", "Needs Clarification")


def scopes_overlap(a, b):
    a, b = a or "All content", b or "All content"
    if "All content" in (a, b):
        return True
    sa, sb = set(a.split(", ")), set(b.split(", "))
    if sa & sb:
        return True
    return bool(("Social media" in sa and sb & tf.SOCIAL) or ("Social media" in sb and sa & tf.SOCIAL))


def _exists(ws, sig):
    return db.fetch_one("SELECT id FROM source_conflicts WHERE workspace_id = ? AND signature = ?", (ws, sig))


def detect(ws, user_id=None):
    """Find new conflicts; returns how many were recorded."""
    found = 0
    rules = repo.list_rules(ws, LIVE)
    dims = {r["id"]: amb.rule_dims(r) for r in rules}
    with db.transaction() as c:
        for a, b in combinations(rules, 2):
            if not (dims[a["id"]] and dims[b["id"]]) or not scopes_overlap(a["scope"], b["scope"]):
                continue
            clash = [d for d in dims[a["id"]] if d in dims[b["id"]] and dims[a["id"]][d] != dims[b["id"]][d]]
            if not clash:
                continue
            d = clash[0]
            sig = f"rule:{min(a['id'], b['id'])}:{max(a['id'], b['id'])}:{d}"
            if _exists(ws, sig):
                continue
            toward, away = (a, b) if dims[a["id"]][d] == "toward" else (b, a)
            where = a["scope"] if a["scope"] != "All content" else b["scope"]
            cid = db.insert("source_conflicts", c=c, workspace_id=ws, kind="rule", signature=sig,
                            title=f"{a['code']} vs {b['code']} · {amb.DIMS[d]['label']}",
                            explanation=(f"{toward['code']} asks for more {amb.DIMS[d]['label'].lower()}, while "
                                         f"{away['code']} asks for less. Both apply to {where}."),
                            status="open", created_at=db.now())
            for r in (a, b):
                db.insert("conflict_sides", c=c, conflict_id=cid, rule_id=r["id"])
            found += 1
        facts = repo.list_facts(ws, ("Pending Validation", "Approved"))
        groups = {}
        for f in facts:
            groups.setdefault((f["product"], f["attribute"], f["unit"]), []).append(f)
        for (prod, attr, unit), fs in groups.items():
            values = sorted({f["value"] for f in fs})
            if len(values) < 2:
                continue
            sig = "fact:" + ":".join(str(i) for i in sorted(f["id"] for f in fs))
            if _exists(ws, sig):
                continue
            ranked = sorted(fs, key=lambda f: -(f["authority_rank"] or 0))
            top, rest = ranked[0], ranked[1:]
            note = (f"Highest authority: {top['doc_title']} ({top['authority_level']}, v{top['doc_version']}). "
                    if (top["authority_rank"] or 0) > max((f["authority_rank"] or 0) for f in rest) else
                    "The sources have equal authority, so a human must decide. ")
            cid = db.insert("source_conflicts", c=c, workspace_id=ws, kind="fact", signature=sig,
                            title=f"{prod} · {attr}: " + " vs ".join(f"{v:g} {unit}" for v in values),
                            explanation=note + "BrandCanon has not chosen a value; confirm the source of truth.",
                            status="open", created_at=db.now())
            for f in fs:
                db.insert("conflict_sides", c=c, conflict_id=cid, fact_id=f["id"])
            found += 1
        if found:
            repo.log(ws, user_id, "Conflicts detected", "conflict", None, f"{found} new", c=c)
    return found


def coverage_gaps(ws):
    """Channels with no specific guidance. Reported as missing guidance — no rule is invented."""
    covered = set()
    for r in repo.list_rules(ws, ("Approved", "Pending Validation", "Needs Clarification")):
        covered |= set((r["scope"] or "").split(", "))
    if covered & tf.SOCIAL:
        covered.add("Social media")
    return [ch for ch in config.CHANNELS if ch != "All content" and ch not in covered]


def resolve_fact_conflict(ws, user_id, conflict_id, keep_fact_id, note):
    require(user_id, "Brand Manager")
    if not (note or "").strip():
        raise ValueError("Please explain the resolution.")
    sides = repo.conflict_sides(conflict_id)
    if keep_fact_id not in [s["id"] for s in sides]:
        raise ValueError("Chosen fact is not part of this conflict.")
    with db.transaction() as c:
        for s in sides:
            db.update("brand_facts", s["id"], c=c, status="Approved" if s["id"] == keep_fact_id else "Superseded")
        db.update("source_conflicts", conflict_id, c=c, status="resolved", resolution=f"source_of_truth:{keep_fact_id}",
                  resolution_note=note.strip(), resolved_by=user_id, resolved_at=db.now())
        repo.log(ws, user_id, "Resolved source conflict", "conflict", conflict_id, note[:100], c=c)


def resolve_rule_conflict(ws, user_id, conflict_id, action, note, rule_id=None, new_scope=None):
    """action: 'rescope' | 'archive' | 'compatible'."""
    require(user_id, "Brand Manager")
    if not (note or "").strip():
        raise ValueError("Please explain the resolution.")
    if action == "rescope":
        if not (rule_id and new_scope):
            raise ValueError("Choose the rule and its new scope.")
        from modules import brand_constitution
        r = repo.get_rule(rule_id)
        brand_constitution.edit_rule(ws, user_id, rule_id, r["text"], f"Scope narrowed to {new_scope}: {note}", scope=new_scope)
    elif action == "archive":
        if not rule_id:
            raise ValueError("Choose the rule to archive.")
        db.update("brand_rules", rule_id, status="Archived", updated_at=db.now())
    elif action != "compatible":
        raise ValueError(f"Unknown resolution {action}")
    with db.transaction() as c:
        db.update("source_conflicts", conflict_id, c=c, status="resolved", resolution=f"{action}:{rule_id or ''}",
                  resolution_note=note.strip(), resolved_by=user_id, resolved_at=db.now())
        repo.log(ws, user_id, "Resolved rule conflict", "conflict", conflict_id, f"{action}: {note[:80]}", c=c)
