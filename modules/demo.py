"""Demo mode: a clearly labelled fictional NovaTech workspace.

Everything is created through the real pipeline (upload → extraction → RuleProbe → audit → review), so the analytics
are computed from real stored records. Past submissions are backdated so trends are visible; they are demo records,
not customer activity, and the UI labels the workspace as a demonstration.
"""
from datetime import datetime, timedelta

import config
from database import db, repositories as repo
from modules import approval_workflow as aw, brand_constitution as bc, document_ingestion as di, rule_probe
from services import gemini_service

DEMO_NAME = "NovaTech (Demo)"
DEMO_POST = "NovaTech guarantees 15 hours of battery life and will completely transform your productivity!"
PEOPLE = [("Neha", "Brand Manager"), ("Kavya", "Reviewer"), ("Priya", "Creator"), ("Arjun", "Creator"),
          ("Meera", "Creator"), ("Rahul", "Creator")]
HISTORY = [
    ("Back-to-campus reel", "Social media caption", "Instagram", "Priya",
     "Heyyy besties, NovaTech X1 is literally insane!!! 15 hours of battery life", 40, "fix"),
    ("Weekend deal post", "Social media caption", "Instagram", "Arjun",
     "Don't miss out! 20% off the NovaTech X1 this weekend only. Buy now or regret it forever!", 34,
     "Save 20% on NovaTech X1 until 30 November. Explore the offer today."),
    ("Durability ad", "Advertisement", "Advertisements", "Meera", "The unbreakable NovaTech X1 weighs just 1.2 kg.", 27, "fix"),
    ("Gaming promo", "Social media caption", "Social media", "Rahul",
     "NovaTech X1: the ultimate machine for professional gamers. Explore it today.", 20, "escalate"),
    ("Battery teaser", "Social media caption", "X / Twitter", "Meera", "Get 12 hours of battery life on NovaTech X1.", 13, "fix"),
    ("Spec card", "Website copy", "Website", "Priya",
     "NovaTech X1: 16 GB memory, 512 GB SSD and a 14-inch 2.8K OLED display. Explore the full specs.", 8, "approve"),
    ("Launch tweet", "Social media caption", "X / Twitter", "Rahul", "Nova X1 is here, the fastest laptop on the market!", 3, "pending"),
]


def users(ws):
    return {n: repo.get_or_create_user(ws, n, r) for n, r in PEOPLE}


def upload_samples(ws, user_id, use_ai=False):
    out = []
    for f in sorted(config.SAMPLE_DIR.iterdir()):
        if f.suffix.lower() in config.ALLOWED_EXTENSIONS:
            out.append(di.ingest(ws, user_id, f.name, f.read_bytes(), use_ai=use_ai))
    return out


def _backdate(sid, days):
    t = lambda h: (datetime.now() - timedelta(days=days) + timedelta(hours=h)).isoformat(timespec="seconds")  # noqa: E731
    with db.transaction() as c:
        c.execute("UPDATE content_submissions SET created_at = ?, updated_at = ? WHERE id = ?", (t(0), t(30), sid))
        for i, r in enumerate(c.execute("SELECT id FROM content_revisions WHERE submission_id = ? ORDER BY revision_no", (sid,)).fetchall()):
            c.execute("UPDATE content_revisions SET created_at = ? WHERE id = ?", (t(i * 20), r["id"]))
            c.execute("UPDATE audit_reports SET created_at = ? WHERE revision_id = ?", (t(i * 20), r["id"]))
        c.execute("UPDATE approvals SET created_at = ? WHERE submission_id = ?", (t(26), sid))
        c.execute("UPDATE decisions SET created_at = ? WHERE submission_id = ?", (t(26), sid))


def reset(with_history=True):
    """Delete and rebuild the demo workspace. Only ever touches the workspace named DEMO_NAME.

    Gemini is switched off while the demo is built, so the demo is reproducible and costs no quota. Everything created here
    is labelled "Demo fallback (deterministic demo data)".
    """
    with gemini_service.suspended():
        return _reset(with_history)


def _reset(with_history):
    old = db.fetch_one("SELECT id FROM workspaces WHERE name = ?", (DEMO_NAME,))
    if old:
        db.execute("DELETE FROM workspaces WHERE id = ?", (old["id"],))  # cascades to all workspace data
    ws = repo.get_or_create_workspace(DEMO_NAME, is_demo=True)
    u = users(ws)
    from modules import auth
    auth.set_demo_passwords(ws)
    if not with_history:
        return ws
    upload_samples(ws, u["Neha"])
    bc.approve_all_pending(ws, u["Neha"], min_authority_rank=3)   # presentation stays pending: low authority
    rule_probe.scan(ws, u["Neha"])
    for title, ctype, channel, author, text, days, plan in HISTORY:
        sid, rev, rid = aw.create_draft(ws, u[author], title, text, ctype, channel, "NovaTech X1", use_ai=False)
        aw.submit(ws, u[author], sid)
        if plan == "pending":
            _backdate(sid, days)
            continue
        if plan == "approve":
            aw.decide(ws, u["Kavya"], sid, "Approved", "Accurate and on-brand; no changes needed.")
        elif plan == "escalate":
            aw.comment(sid, u["Kavya"], "Is gaming an approved audience for X1? Escalating to the brand team.", 1)
            aw.decide(ws, u["Kavya"], sid, "Escalated", "Positioning question: gaming is not an approved audience.")
        else:
            aw.decide(ws, u["Kavya"], sid, "Changes requested", "Please fix the flagged issues before publishing.")
            fs = repo.findings(rid)
            if plan == "fix":
                reps = {i: f["suggestion"] for i, f in enumerate(fs) if f["suggestion"] and f["span_end"]}
                aw.apply_and_revise(ws, u[author], sid, fs, reps)
            else:
                aw.add_revision(ws, u[author], sid, plan, "Rewrote the offer post")
            aw.decide(ws, u["Kavya"], sid, "Approved", "Claims now match approved sources and tone is acceptable.")
        _backdate(sid, days)
    return ws
