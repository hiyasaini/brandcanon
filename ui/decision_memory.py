"""Decision Memory — authorised reviewer decisions, retrieved as context for future reviews.

A past decision is advice, never policy: it does not become a brand rule, and its source and version are checked
(stale precedents are flagged) before it is offered. Authorised reviewers can override a decision with an explanation;
the old one stays in history.
"""
import streamlit as st

from modules import approval_workflow as aw, decision_memory as dm, queries as q
from services import gemini_service as gs
from ui import components as c
from ui import styles as S

ss = st.session_state
REVIEWERS = ("Reviewer", "Brand Manager")


def _precedent_summary(f):
    key = f"ps{f['id']}"
    if not gs.enabled():
        return
    if st.button("Summarise these precedents with Gemini", key=f"b{key}", icon=":material/auto_awesome:"):
        with st.spinner("Summarising earlier decisions…"):
            try:
                ss[key] = dm.summarise_precedents(f, f["precedents"])
            except (gs.GeminiError, ValueError) as e:
                ss[key] = {"error": str(e)}
    out = ss.get(key)
    if out and out.get("error"):
        st.error(f"No summary: {out['error']}", icon=":material/cloud_off:")
    elif out:
        st.markdown(f'<div class="bc-evidence">{c.esc(out["summary"])}<div class="src">Based on decisions '
                    f'{", ".join("#" + str(i) for i in out["decision_ids"])} · advice only — the reviewer decides</div></div>'
                    + c.engine_tag(out["engine"]), unsafe_allow_html=True)


def _detail(ws, user, sid):
    sub = q.get_submission(sid)
    revs = q.revisions(sid)
    with c.card():
        a, b = st.columns([3, 1])
        a.markdown(f"### {c.esc(sub['title'])}  \n<span class='bc-muted'>#{sid} · {sub['content_type']} · {sub['channel']} · "
                   f"{sub['product'] or '—'} · by {c.esc(sub['author_name'])}</span>", unsafe_allow_html=True)
        b.markdown(c.badge(sub["status"]), unsafe_allow_html=True)
        labels = [f"Revision {r['revision_no']}" for r in revs]
        pick = st.radio("Revision", labels, index=len(labels) - 1, horizontal=True, key=f"rv{sid}") if len(revs) > 1 else labels[0]
        rev = revs[labels.index(pick)]
        rep, fs = aw.report_with_context(ws, rev["id"], exclude_submission=sid)
        st.markdown(c.highlighted(rev["text"], fs), unsafe_allow_html=True)
        st.markdown(f"<span class='bc-muted'>{rev['note'] or ''} · {c.esc(rev['created_by_name'])} · {rev['created_at'][:16].replace('T', ' ')}"
                    f" · audit: {rep['overall_status'] if rep else '—'}</span>", unsafe_allow_html=True)
        if rep:
            st.markdown('<div class="bc-prov">Audit produced by ' + c.engine_tag(rep["engine"]) + "</div>", unsafe_allow_html=True)
            c.engine_alert(rep["engine"])
        if len(revs) > 1 and rev["revision_no"] > 1:
            st.markdown("**Changes from revision 1**")
            st.markdown(c.diff(revs[0]["text"], rev["text"]), unsafe_allow_html=True)
        st.write("")
        for i, f in enumerate(fs):
            title = f"{i + 1}. {f['severity'].capitalize()} · {f['category']} · {f['classification']} — {(f['quote'] or f['message'])[:70]}"
            with st.expander(title, expanded=f["classification"] != "Verified" and f["disposition"] == "open" and i < 3):
                st.markdown(c.badge("root cause: " + f["root_cause"], "lavender") + c.badge(f["confidence"] + " confidence", "neutral")
                            + (c.badge(f["disposition"]) if f["disposition"] != "open" else ""), unsafe_allow_html=True)
                st.markdown(c.esc(f["message"]))
                st.markdown(c.finding_trail(f, (f.get("precedents") or [None])[0]), unsafe_allow_html=True)
                st.markdown(c.evidence(f["evidence_text"], f["evidence_source"]), unsafe_allow_html=True)
                if f["suggestion"]:
                    st.markdown(f"Suggested correction: “{c.esc(f['suggestion'])}”")
                if f["disposition_reason"]:
                    st.caption(f"{f['disposition']}: {f['disposition_reason']}")
                for p in f.get("precedents", []):
                    st.markdown(f"<div class='bc-precedent'><b>An earlier review addressed a similar claim.</b> "
                                f"{c.esc(p['summary'])}</div>", unsafe_allow_html=True)
                    if st.button("View previous decision", key=f"pv{f['id']}_{p['id']}", type="tertiary",
                                 icon=":material/history_edu:"):
                        ss["dm_decision"], ss["dm_tab"] = p["id"], "Decision history"
                        st.rerun()
                if f.get("precedents"):
                    _precedent_summary(f)
                if (user["role"] in REVIEWERS and f["classification"] != "Verified" and f["disposition"] != "dismissed"
                        and rev["id"] == revs[-1]["id"] and sub["status"] in ("In review", "Escalated")):
                    why = st.text_input("Override: why is this acceptable here?", key=f"ov{f['id']}")
                    if st.button("Override finding", key=f"ovb{f['id']}", disabled=not why.strip()):
                        if c.run_action(aw.override_finding, ws, user["id"], sid, f["id"], why,
                                        success="Override saved to Decision Memory"):
                            st.rerun()
    with c.card():
        st.markdown("#### Comments")
        for cm in q.comments(sid):
            st.markdown(f"<span class='bc-muted'>{c.esc(cm['user_name'])} ({cm['user_role']}) · v{cm['revision_no'] or '—'} · "
                        f"{cm['created_at'][:16].replace('T', ' ')}</span><br>{c.esc(cm['text'])}", unsafe_allow_html=True)
        msg = st.text_input("Add a comment", key=f"rc{sid}")
        if st.button("Post", key=f"rcb{sid}", disabled=not msg.strip()):
            if c.run_action(aw.comment, sid, user["id"], msg, revs[-1]["revision_no"]):
                st.rerun()
    for a in q.approvals(sid):
        st.markdown(f"{c.badge(a['outcome'])} <span class='bc-muted'>{c.esc(a['reviewer_name'])} · revision {a['revision_no']} · "
                    f"{a['created_at'][:10]}</span> — {c.esc(a['rationale'])}", unsafe_allow_html=True)
    if sub["status"] in ("In review", "Escalated"):
        with c.card():
            st.markdown(f"#### Decision on revision {revs[-1]['revision_no']}")
            need = ("Brand Manager",) if sub["status"] == "Escalated" else REVIEWERS
            if user["role"] not in need:
                st.info(f"This decision is for: {' or '.join(need)}.", icon=":material/lock:")
                return
            why = st.text_area("Rationale (required — it is saved as precedent)", key=f"why{sid}",
                               placeholder="e.g. The battery claim now matches the approved specification.")
            bar = st.container(horizontal=True, gap="small")
            opts = [("Approve", "Approved", "primary"), ("Request changes", "Changes requested", "secondary"),
                    ("Reject", "Rejected", "secondary"), ("Escalate", "Escalated", "secondary")]
            for label, outcome, kind in opts:
                if outcome == "Escalated" and sub["status"] == "Escalated":
                    continue
                if bar.button(label, key=f"d{outcome}{sid}", type=kind, disabled=not why.strip()):
                    if c.run_action(aw.decide, ws, user["id"], sid, outcome, why, success=f"{outcome} — saved to Decision Memory"):
                        st.rerun()


def _queue(ws, user):
    subs = q.list_submissions(ws, ("In review", "Escalated"))
    if not subs:
        c.empty("The review queue is empty", "Content submitted from the Content Auditor appears here.")
        return
    left, right = st.container(key="wrap-dmq").columns([1, 2.4])
    ids = [s["id"] for s in subs]
    if (nav := c.take("dm_sub")) in ids:
        ss.rq_sel = nav
    sel = ss.get("rq_sel") if ss.get("rq_sel") in ids else ids[0]
    with left, st.container(key="stick-dmq"):
        with c.card(key="card-dmqsum"):
            from collections import Counter
            c.card_title("Review queue", f"{len(subs)} waiting")
            by_status = Counter(s_["status"] for s_ in subs)
            by_channel = Counter(s_["channel"] for s_ in subs)
            oldest = min(s_["created_at"] for s_ in subs)[:10]
            st.markdown(c.chart_stat([(by_status.get("In review", 0), "in review"), (by_status.get("Escalated", 0), "escalated")])
                        + c.rank_rows([(c.esc(ch), n, ch) for ch, n in by_channel.most_common()], S.CH_GREEN)
                        + f"<div class='bc-muted' style='margin-top:6px'>Oldest submission: {oldest}</div>", unsafe_allow_html=True)
        for s in subs:
            revs = q.revisions(s["id"])
            rep = q.latest_report(revs[-1]["id"])
            with c.card():
                st.markdown(f"**{c.esc(s['title'])}**<br><span class='bc-muted'>{s['channel']} · v{s['latest_revision']} · "
                            f"{c.esc(s['author_name'])}</span><br>{c.badge(s['status'])}{c.badge(rep['overall_status']) if rep else ''}",
                            unsafe_allow_html=True)
                if st.button("Open", key=f"q{s['id']}", type="primary" if s["id"] == sel else "secondary", width="stretch"):
                    ss.rq_sel = s["id"]
                    st.rerun()
    with right:
        _detail(ws, user, sel)


def _history(ws, user):
    rows = q.list_decisions(ws)
    if not rows:
        c.empty("No decisions yet", "Decisions are saved when reviewers approve, request changes, reject, escalate or override "
                "findings. Each one becomes context for future reviews.")
        return
    superseded = {r["supersedes_decision_id"]: r["id"] for r in rows if r["supersedes_decision_id"]}
    opt = lambda key: ["Any"] + sorted({str(r[key]) for r in rows if r[key]})  # noqa: E731
    left, mid, right = st.container(key="wrap-dm").columns([0.82, 1.45, 1.35])
    stick = left.container(key="stick-dmf")
    with stick, c.card(key="card-dmfilters"):
        c.card_title("Search and filters")
        phrase = st.text_input("Content phrase", key="dmf_q", placeholder="e.g. battery, guaranteed")
        rule = st.selectbox("Rule", opt("rule_code"), key="dmf_rule")
        product = st.selectbox("Product", opt("product"), key="dmf_prod")
        campaign = st.selectbox("Campaign", opt("campaign"), key="dmf_camp")
        reviewer = st.selectbox("Reviewer", opt("reviewer_name"), key="dmf_rev")
        period = st.selectbox("Date", ["All time", "Last 7 days", "Last 30 days", "Last 90 days"], key="dmf_period")
        status = st.selectbox("Decision status", ["Any", "Active", "Superseded"] + sorted({r["decision"] for r in rows}), key="dmf_st")
    from datetime import date, timedelta
    days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}.get(period)
    lo, hi = ((date.today() - timedelta(days=days)).isoformat() if days else "0000"), "9999"
    view = [r for r in rows
            if (not phrase or phrase.lower() in f"{r['claim_text']} {r['explanation']} {r['submission_title'] or ''}".lower())
            and (product == "Any" or r["product"] == product) and (rule == "Any" or r["rule_code"] == rule)
            and (campaign == "Any" or r["campaign"] == campaign) and (reviewer == "Any" or r["reviewer_name"] == reviewer)
            and (status == "Any" or (status == "Active" and r["id"] not in superseded) or (status == "Superseded" and r["id"] in superseded)
                 or r["decision"] == status)
            and lo <= r["created_at"][:10] <= hi]
    if (pending := c.take("dm_pending_sel")) is not None:
        ss["dm_sel"] = pending
    if (nav := c.take("dm_decision")) is not None:
        ss["dm_sel"] = nav
        if nav not in [r["id"] for r in view]:
            view = [r for r in rows if r["id"] == nav] + view
    ids = [r["id"] for r in view]
    sel = ss.get("dm_sel") if ss.get("dm_sel") in ids else (ids[0] if ids else None)
    with stick, c.card(key="card-dmsum"):
        from collections import Counter
        c.card_title("In this view", f"{len(view)} decisions")
        kinds = Counter(r["decision"] for r in view)
        st.markdown(c.rank_rows([(c.esc(k), n, k) for k, n in kinds.most_common()], S.CH_GREEN)
                    + (f"<div class='bc-muted' style='margin-top:6px'>{len([r for r in view if r['id'] in superseded])} superseded "
                       f"· {len({r['reviewer_name'] for r in view if r['reviewer_name']})} reviewers</div>" if view else ""),
                    unsafe_allow_html=True)
    first_text = {}
    with mid:
        st.caption(f"{len(view)} of {len(rows)} decisions · precedents are advice for reviewers and never change rules.")
        with st.container(height=900, border=False):
            for r in view[:40]:
                stale = r["source_title"] and r["source_current"] == 0
                f = q.finding(r["finding_id"]) if r["finding_id"] else None
                if r["submission_id"] and r["submission_id"] not in first_text:
                    revs = q.revisions(r["submission_id"])
                    first_text[r["submission_id"]] = revs[0]["text"] if revs else ""
                original = first_text.get(r["submission_id"], "")
                on = r["id"] == sel
                with c.card(key=f"card-dm{r['id']}"):
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;gap:8px'><div>{c.badge(r['decision'])}"
                        f"{c.badge('superseded', 'neutral') if r['id'] in superseded else ''}"
                        f"{c.badge('older source version', 'amber') if stale else ''}</div>"
                        f"<span class='bc-mono'>{r['created_at'][:16].replace('T', ' ')}</span></div>"
                        f"<div class='bc-muted' style='margin-top:6px;font-size:.74rem'>ORIGINAL CONTENT</div>"
                        f"<div style='font-size:.86rem;line-height:1.45'>{c.esc(original[:150]) or '—'}</div>"
                        f"<div class='bc-muted' style='margin-top:6px;font-size:.74rem'>FINDING</div>"
                        f"<div style='font-size:.86rem'>“{c.esc((r['claim_text'] or '')[:90])}”"
                        f"{' · ' + c.esc(f['classification']) if f else (' · ' + c.esc(r['finding_category']) if r['finding_category'] else '')}</div>"
                        f"<div class='bc-muted' style='margin-top:6px;font-size:.74rem'>REASONING</div>"
                        f"<div style='font-size:.86rem'>{c.esc(r['explanation'][:160])}</div>"
                        f"<div class='bc-mono' style='margin-top:8px'>{c.esc(r['rule_code'] or 'no rule')} · "
                        f"{c.esc((r['source_title'] or 'no source document') + (' · v' + r['source_version'] if r['source_version'] else ''))}"
                        f" · {c.esc(r['reviewer_name'] or '')}</div>", unsafe_allow_html=True)
                    if st.button("Selected" if on else "View decision", key=f"dmo{r['id']}", type="primary" if on else "tertiary",
                                 icon=":material/chevron_right:" if not on else ":material/check:", icon_position="right"):
                        ss["dm_sel"] = r["id"]
                        st.rerun()
            if len(view) > 40:
                st.caption(f"Showing 40 of {len(view)}. Narrow the filters to see the rest.")
    with right, st.container(key="stick-dmd"):
        if sel:
            _decision_detail(ws, user, next(r for r in rows if r["id"] == sel), superseded)
        else:
            c.empty("No decision matches", "Change the filters.")


def _decision_detail(ws, user, r, superseded):
    with st.container(key="darkpanel-dm", border=True):
        st.markdown(f"<div class='bc-mono'>Decision #{r['id']} · {r['created_at'][:16].replace('T', ' ')} · "
                    f"{c.esc(r['reviewer_name'] or '')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='bc-specimen-rule'>{c.esc(r['decision'])}</div>", unsafe_allow_html=True)
        if r["id"] in superseded:
            st.markdown(c.badge("Superseded — no longer offered as precedent", "neutral"), unsafe_allow_html=True)
            if st.button(f"Open the overriding decision #{superseded[r['id']]}", key=f"sup{r['id']}", type="tertiary",
                         icon=":material/arrow_outward:", icon_position="right"):
                ss["dm_sel"] = superseded[r["id"]]
                st.rerun()
        if r["supersedes_decision_id"]:
            st.markdown(c.badge(f"Overrides decision #{r['supersedes_decision_id']}", "amber"), unsafe_allow_html=True)
        st.markdown("**Reasoning**")
        st.markdown(f"<div style='font-size:.95rem'>{c.esc(r['explanation'])}</div>", unsafe_allow_html=True)
        f = q.finding(r["finding_id"])
        stale = r["source_title"] and r["source_current"] == 0
        st.markdown(c.evidence_trail([
            ("Content", f"“{r['claim_text'][:60]}”", ""),
            ("Finding", f"{f['classification']} · {f['category']}" if f else (r["finding_category"] or "whole submission"), ""),
            ("Rule", r["rule_code"] or "none recorded", "" if r["rule_code"] else "missing"),
            ("Source", f"{r['source_title']} v{r['source_version']}" + (" (no longer current)" if stale else "")
             if r["source_title"] else "Source reference unavailable", "" if r["source_title"] else "missing"),
            ("Decision", f"{r['decision']} · {r['reviewer_name'] or ''}", "decision")]), unsafe_allow_html=True)
        if stale:
            st.warning("This decision relied on a source version that is no longer current. Check the current source before "
                       "using it as precedent.", icon=":material/history:")
        if f and f["evidence_text"]:
            st.markdown(c.quote(f["evidence_text"], f["evidence_source"]), unsafe_allow_html=True)
        sub = q.get_submission(r["submission_id"]) if r["submission_id"] else None
        if sub:
            revs = q.revisions(sub["id"])
            st.markdown(f"**Original and corrected content** <span class='bc-muted'>· {c.esc(sub['title'])} · "
                        f"{len(revs)} revision(s) · {c.esc(sub['product'] or '—')} · {c.esc(sub['channel'])}</span>",
                        unsafe_allow_html=True)
            st.markdown(c.diff(revs[0]["text"], revs[-1]["text"]) if len(revs) > 1 else c.highlighted(revs[0]["text"], []),
                        unsafe_allow_html=True)
            st.markdown(f"**Approval status** {c.badge(sub['status'])}", unsafe_allow_html=True)
            events = [{"at": a["created_at"], "who": a["reviewer_name"], "label": f"{a['outcome']} · revision {a['revision_no']}",
                       "detail": a["rationale"], "tone": "olive" if a["outcome"] == "Approved" else "amber"} for a in q.approvals(sub["id"])]
            events += [{"at": d["created_at"], "who": d["reviewer_name"], "label": d["decision"], "detail": d["claim_text"][:90],
                        "tone": "terracotta"} for d in q.decisions_for_submission(sub["id"]) if d["decision"].startswith("Finding")]
            st.markdown("**Review history**")
            st.markdown(c.timeline(sorted(events, key=lambda e: e["at"])), unsafe_allow_html=True)
        if r["approved_correction"]:
            st.markdown(f"Approved wording: “{c.esc(r['approved_correction'])}”")
        if r["id"] not in superseded and user["role"] in REVIEWERS and r["decision"] in ("Finding upheld", "Finding overridden"):
            with st.expander("Override this decision"):
                st.caption("The earlier decision stays in history but will no longer be offered as precedent.")
                why = st.text_input("Explanation (required)", key=f"odx{r['id']}")
                if st.button("Save overriding decision", disabled=not why.strip(), type="primary", key=f"odb{r['id']}"):
                    nid = c.run_action(dm.override, ws, user["id"], r["id"], why, success="Earlier decision overridden")
                    if nid:
                        ss["dm_pending_sel"] = nid
                        st.rerun()


def _issues(rev_id):
    rep = q.latest_report(rev_id)
    if not rep:
        return None
    return sum(1 for f in q.findings(rep["id"]) if f["classification"] != "Verified" and f["disposition"] != "dismissed")


def _approvals(ws):
    subs = q.list_submissions(ws, ("Approved", "Rejected", "Changes requested", "Escalated"))
    if not subs:
        c.empty("No approvals yet", "Completed reviews appear here with their full revision history.")
        return
    from collections import Counter
    outcomes = Counter(s_["status"] for s_ in subs)
    revs_n = [s_["latest_revision"] for s_ in subs]
    m = st.container(key="pair-dmah").columns(4)
    for col, (label, val, note, tone, icon) in zip(m, [
            ("Completed reviews", len(subs), "submissions with a final or current decision", "forest", "review"),
            ("Approved", outcomes.get("Approved", 0), "published after review", "ok", "decision"),
            ("Changes requested", outcomes.get("Changes requested", 0), "sent back to the creator", "warn", "repeat"),
            ("Revisions per item", f"{sum(revs_n) / len(revs_n):.1f}", "on average, first draft included", "accent", "audit")]):
        with col:
            c.metric(label, val, note, tone, icon=icon)
    st.write("")
    for s in subs:
        revs = q.revisions(s["id"])
        apprs = q.approvals(s["id"])
        with c.card(key=f"card-ah{s['id']}"):
            st.markdown(f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap'>"
                        f"<div><div class='bc-card-title' style='margin:0'>{c.esc(s['title'])}</div>"
                        f"<div class='bc-muted'>{c.esc(s['content_type'])} · {c.esc(s['channel'])} · {c.esc(s['author_name'])} · "
                        f"{len(revs)} revision{'s' if len(revs) != 1 else ''}</div></div><div>{c.badge(s['status'])}</div></div>",
                        unsafe_allow_html=True)
            left, right = st.container(key=f"pair-ah{s['id']}").columns([1, 1.25])
            with left:
                st.markdown("<div class='bc-kg-h' style='color:inherit;opacity:.7'>Timeline</div>", unsafe_allow_html=True)
                events = [{"at": r["created_at"], "who": r["created_by_name"], "label": f"Revision {r['revision_no']}",
                           "detail": r["text"], "tone": "terracotta"} for r in revs]
                events += [{"at": a["created_at"], "who": a["reviewer_name"], "label": f"{a['outcome']} · revision {a['revision_no']}",
                            "detail": a["rationale"], "tone": "olive" if a["outcome"] == "Approved" else "amber"} for a in apprs]
                st.markdown(c.timeline(sorted(events, key=lambda e: e["at"])), unsafe_allow_html=True)
            with right:
                st.markdown("<div class='bc-kg-h' style='color:inherit;opacity:.7'>First draft → latest revision</div>",
                            unsafe_allow_html=True)
                if len(revs) > 1:
                    n0, n1 = _issues(revs[0]["id"]), _issues(revs[-1]["id"])
                    if n0 is not None and n1 is not None:
                        st.markdown(c.before_after(revs[0]["text"], revs[-1]["text"], n0, n1), unsafe_allow_html=True)
                    st.markdown("<div class='bc-muted' style='margin:10px 0 4px'>Word-level changes</div>" + c.diff(revs[0]["text"],
                                revs[-1]["text"]), unsafe_allow_html=True)
                else:
                    st.markdown(c.quote(revs[0]["text"], f"Revision 1 · {revs[0]['created_by_name']}") if revs else "",
                                unsafe_allow_html=True)
                    st.caption("Only one revision: the decision applied to the first draft.")


def render():
    ws, user = c.ctx()
    c.flash()
    c.page_head("Decision Memory", "Remember the reasoning behind every authorised decision.")
    queue = q.list_submissions(ws, ("In review", "Escalated"))
    if ss.get("dm_sub") is not None:
        ss["dm_tab"] = "Review queue"
    elif ss.get("dm_decision") is not None and "dm_tab" not in ss:
        ss["dm_tab"] = "Decision history"
    t = c.tabs(["Review queue", "Decision history", "Approval history"], "dm_tabs", "dm_tab")
    with t[0]:
        st.caption(f"{len(queue)} item(s) waiting for a decision.")
        _queue(ws, user)
    with t[1]:
        _history(ws, user)
    with t[2]:
        _approvals(ws)
