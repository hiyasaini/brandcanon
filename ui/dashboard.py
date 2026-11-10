"""Overview — Brand Intelligence Overview. Every number and chart is computed from the database."""
from collections import Counter

import plotly.graph_objects as go_
import streamlit as st

from database import db
from modules import governance_analytics as ga, queries as q, rule_probe
from ui import components as c, tour
from ui import styles as S

ss = st.session_state


def _count(sql, ws):
    return db.fetch_one(sql, (ws,))["n"]


def _review_queue(ws):
    """Rules a person still has to look at: extracted but unreviewed, flagged, or with an open RuleProbe finding."""
    out = [(r, r["status"], "constitution", {"con_rule": r["id"]}) for r in q.list_rules(ws, ("Pending Validation", "Needs Clarification"))]
    seen = {r["id"] for r, *_ in out}
    for x in rule_probe.open_findings(ws):
        if x["rule"]["id"] not in seen:
            out.append((x["rule"], f"Potential {x['test']['classification'].lower()}", "ruleprobe", {"probe_rule": x["rule"]["id"]}))
    return out


def _row(color, title, sub, when="", shape="3px"):
    sub = f"{when} · {sub}" if when else sub
    return (f'<div class="bc-row"><div class="ic" style="background:{color}2E"><span style="width:10px;height:10px;'
            f'border-radius:{shape};background:{color};display:block"></span></div><div class="b"><div class="t">{c.esc(title)}</div>'
            f'<div class="s">{c.esc(sub)}</div></div></div>')


def _open(key):
    return st.button("", key=key, type="tertiary", icon=":material/arrow_outward:", help="Open")


def _health(ws, rules, conflicts):
    """Brand Health: rules by review status, the knowledge chain, and what is still open."""
    with c.card(key="card-health"):
        c.card_title("Brand health", "approved knowledge in force")
        st_counts = Counter(r["status"] for r in rules)
        total = sum(st_counts.values()) or 1
        appr, pend, clar = st_counts.get("Approved", 0), st_counts.get("Pending Validation", 0), st_counts.get("Needs Clarification", 0)
        a, b = st.columns([1, 1.25], vertical_alignment="center")
        with a:
            fig = go_.Figure(go_.Pie(values=[appr, pend, clar] if total else [1], labels=["Approved", "Pending review",
                                     "Needs clarification"], hole=.72, sort=False, textinfo="none",
                                     marker=dict(colors=[S.GREEN, S.YELLOW, S.CORAL], line=dict(color="#fff", width=2)),
                                     hovertemplate="%{label}: %{value}<extra></extra>"))
            fig.add_annotation(text=f"<b>{appr / total:.0%}</b><br><span style='font-size:11px;color:{S.MUTED}'>approved</span>",
                               showarrow=False, font=dict(size=22, family="Manrope, Inter, sans-serif", color=S.TEXT))
            fig.update_layout(showlegend=False)
            st.plotly_chart(c.plot_layout(fig, 190), width="stretch", config={"displayModeBar": False}, key="health_pie")
        with b:
            st.markdown(f'<div class="bc-big">{appr}<small>of {total} rules approved</small></div>'
                        + c.legend([(f"Approved · {appr}", S.GREEN), (f"Pending review · {pend}", S.YELLOW),
                                    (f"Needs clarification · {clar}", S.CORAL)]), unsafe_allow_html=True)
            facts = _count("SELECT COUNT(*) n FROM brand_facts WHERE workspace_id = ? AND status = 'Approved'", ws)
            docs = _count("SELECT COUNT(*) n FROM documents WHERE workspace_id = ? AND status = 'active'", ws)
            st.markdown(f"<div class='bc-muted' style='margin-top:10px'>{docs} source documents · {facts} approved product facts · "
                        f"<b style='color:{S.CORAL_TEXT if conflicts else S.GREEN_TEXT}'>{conflicts} unresolved conflict"
                        f"{'s' if conflicts != 1 else ''}</b></div>", unsafe_allow_html=True)
        # the connected knowledge chain (Evidence Trail, end to end)
        tests = _count("SELECT COUNT(*) n FROM rule_tests t JOIN brand_rules r ON r.id = t.rule_id WHERE r.workspace_id = ?", ws)
        finds = _count("""SELECT COUNT(*) n FROM audit_findings f JOIN audit_reports a ON a.id = f.report_id
                          WHERE a.workspace_id = ? AND f.classification != 'Verified'""", ws)
        decs = _count("SELECT COUNT(*) n FROM decisions WHERE workspace_id = ?", ws)
        docs_n = _count("SELECT COUNT(*) n FROM documents WHERE workspace_id = ? AND status = 'active'", ws)
        chain = [("Documents", docs_n, "document"), ("Rules", appr, "rule"), ("Tests", tests, "case"),
                 ("Findings", finds, "finding"), ("Decisions", decs, "decision")]
        st.markdown('<div class="bc-trail" style="margin-top:12px">' + '<div class="link"></div>'.join(
            f'<div class="node k-{ {"document": "document", "rule": "rule", "case": "test", "finding": "finding", "decision": "decision"}[k]}">'
            f'<div class="k">{t}</div><div class="v" style="font-size:.9rem;font-weight:600">{n}</div></div>' for t, n, k in chain)
            + "</div>", unsafe_allow_html=True)
        if st.button("Explore the Brand Knowledge Graph", key="ov_graph", type="tertiary", icon=":material/hub:"):
            c.go("graph")


def _trends(S_):
    with c.card(key="card-trends"):
        c.card_title("Governance trends", "first-draft findings per week, by root cause")
        wk = S_["weekly_root"]
        if not wk:
            st.caption("No audits yet. Trends appear once content has been audited.")
            return
        weeks = list(wk)
        totals = [sum(wk[w].values()) for w in weeks]
        peak = max(range(len(weeks)), key=lambda i: totals[i])
        keys, _ = c.week_ticks(weeks)
        st.markdown(c.chart_stat([(sum(totals), "findings"), (totals[-1], f"in {keys[-1].split(' · ')[0]}, the latest week"),
                                  (totals[peak], f"at the peak, {keys[peak].split(' · ')[0]}")]), unsafe_allow_html=True)
        series = [("Unresolved issue" if k == "Unresolved / other" else k, S.ROOT_CHART[k], [wk[w].get(k, 0) for w in weeks])
                  for k in ("Creator error", "Guideline defect", "Source conflict", "Knowledge gap", "Unresolved / other")]
        st.plotly_chart(c.weekly_bars(weeks, series, 250), width="stretch", config={"displayModeBar": False}, key="trend_area")


def _investigations(ws):
    with c.card(key="card-inv"):
        tests = list(reversed(q.all_tests(ws)))[:6]
        c.card_title("Recent investigations", "RuleProbe")
        if not tests:
            st.caption("No rules tested yet. Open RuleProbe to examine a rule.")
        for i, t in enumerate(tests):
            tone = {"Ambiguous rule": S.YELLOW, "Contradictory rules": S.CORAL, "Missing guidance": S.PINK,
                    "Model uncertainty": S.PINK, "Clear rule": S.GREEN}.get(t["classification"], S.MINT)
            a, b = st.columns([6, 1], vertical_alignment="center", gap="small")
            a.markdown(_row(tone, f"{t['code']} · {t['classification']}",
                            f"{t['divergence']:.0%} divergence · {c.INVESTIGATION_LABEL.get(t['investigation_state'], '')}",
                            t["created_at"][5:10]), unsafe_allow_html=True)
            with b:
                go_ = _open(f"inv{i}")
            if go_:
                c.go("ruleprobe", probe_rule=t["rule_id"])


def _audits(ws, S_):
    with c.card(key="card-aud"):
        c.card_title("Content audit activity", f"{S_['n_reports']} audits · {S_['n_submissions']} pieces of content")
        cls = S_["classifications"]
        rows = [("Contradicted", S.CORAL), ("Unsupported", S.YELLOW), ("Unverifiable", S.PINK)]
        cats = S_["categories"].most_common(4)
        if not S_["n_reports"]:
            st.caption("No content audited yet.")
            return
        total = sum(cls.get(k, 0) for k, _ in rows) or 1
        st.markdown('<div class="bc-bar" style="margin:8px 0 2px">' + "".join(
            f'<i style="width:{cls.get(k, 0) / total * 100:.1f}%;background:{col}"></i>' for k, col in rows) + "</div>"
            + c.legend([(f"{k} · {cls.get(k, 0)}", col) for k, col in rows]), unsafe_allow_html=True)
        st.markdown("<div class='bc-muted' style='margin:12px 0 4px'>Issues by category (first drafts)</div>", unsafe_allow_html=True)
        mx = max([n for _, n in cats] or [1])
        for k, n in cats:
            st.markdown(f"<div style='display:flex;align-items:center;gap:10px;font-size:.84rem;margin:4px 0'>"
                        f"<span style='width:42%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{c.esc(k)}</span>"
                        f"<span class='bc-bar' style='flex:1;height:8px'><i style='width:{n / mx * 100:.0f}%;background:{S.GREEN}'></i></span>"
                        f"<b style='width:22px;text-align:right'>{n}</b></div>", unsafe_allow_html=True)
        status = S_["status_counts"]
        st.markdown(f"<div class='bc-muted' style='margin-top:10px'>{status.get('In review', 0)} in review · "
                    f"{status.get('Approved', 0)} approved · {status.get('Changes requested', 0)} changes requested</div>",
                    unsafe_allow_html=True)


def _decisions(ws):
    with c.card(key="card-dec"):
        decs = q.list_decisions(ws)[:6]
        c.card_title("Recent decisions", "Decision Memory")
        if not decs:
            st.caption("No reviewer decisions yet.")
        for i, d in enumerate(decs):
            a, b = st.columns([6, 1], vertical_alignment="center", gap="small")
            a.markdown(_row(S.LAVENDER, f"{d['decision']} · {(d['claim_text'] or d['submission_title'] or '')[:60]}",
                            f"{d['reviewer_name'] or ''} · {(d['explanation'] or '')[:70]}", d["created_at"][5:10], "2px"),
                       unsafe_allow_html=True)
            with b:
                go_ = _open(f"dec{i}")
            if go_:
                c.go("decisions", dm_decision=d["id"])


def _attention(ws, user, S_):
    with c.card(key="card-att"):
        c.card_title("Areas requiring attention", "from stored records")
        conf = q.list_conflicts(ws, "open")
        pending = q.list_submissions(ws, ("In review", "Escalated"))
        rec = ga.recurring_violations(S_)
        queue = _review_queue(ws)
        cols = st.container(key="pair-att").columns(4)
        groups = [
            ("Unresolved conflicts", S.CORAL, [(x["title"], (x["explanation"] or "")[:80], "ruleprobe", {"probe_tab": "Conflicts"})
                                               for x in conf]),
            ("Rules awaiting review", S.YELLOW, [(f"{r['code']} · {label}", r["text"][:80], page, state) for r, label, page, state in queue]),
            ("Content awaiting approval", S.LAVENDER, [(s["title"], f"{s['status']} · {s['author_name'] or ''}", "decisions",
                                                        {"dm_sub": s["id"]}) for s in pending]),
            ("Recurring problems", S.PINK, [(x["label"], f"in {x['count']} pieces of content", "governance", {}) for x in rec]),
        ]
        for col, (title, color, items) in zip(cols, groups):
            with col:
                st.markdown(f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px'><span style='width:9px;"
                            f"height:9px;border-radius:50%;background:{color}'></span><b style='font-size:.86rem'>{c.esc(title)}</b>"
                            f"<span class='bc-badge' style='background:{color}2E;color:{S.TEXT};margin:0 0 0 auto'>{len(items)}</span></div>",
                            unsafe_allow_html=True)
                if not items:
                    st.caption("Nothing open.")
                for i, (t, s, page, state) in enumerate(items[:3]):
                    st.markdown(f"<div style='font-size:.84rem;font-weight:600;line-height:1.3;margin-top:6px'>{c.esc(t[:70])}</div>"
                                f"<div class='bc-muted' style='font-size:.76rem'>{c.esc(s)}</div>", unsafe_allow_html=True)
                    if st.button("Open", key=f"att{title[:4]}{i}", type="tertiary"):
                        c.go(page, **state)
                if len(items) > 3:
                    st.caption(f"+ {len(items) - 3} more")


def render():
    ws, user = c.ctx()
    c.flash()

    def new_audit():
        c.go("auditor", aud_new=True)
    c.page_head("Brand Intelligence Overview", "Understand your brand. Investigate inconsistencies. Maintain control.",
                [("Upload documents", lambda: c.go("constitution", con_tab="Upload"), "secondary", ":material/upload_file:"),
                 ("New content audit", new_audit, "primary", ":material/add:")])
    ws_row = next(w for w in q.list_workspaces() if w["id"] == ws)
    tour.offer(ws_row)

    if not q.list_documents(ws):
        c.empty("No brand knowledge yet", "Upload your brand guidelines, product specifications or policies (PDF or DOCX). "
                "Extracted rules wait for your review before they are used.")
        c.nav_button("Upload documents", "constitution", "empty_up", {"con_tab": "Upload"}, kind="primary",
                     icon=":material/upload_file:")
        return
    if ws_row["is_demo"]:
        c.illustrative()
        st.write("")

    rules = q.list_rules(ws, ("Approved", "Pending Validation", "Needs Clarification"))
    approved = sum(r["status"] == "Approved" for r in rules)
    review = len(_review_queue(ws))
    audits = _count("SELECT COUNT(*) n FROM audit_reports WHERE workspace_id = ?", ws)
    conflicts = len(q.list_conflicts(ws, "open"))
    m = st.columns(4)
    with m[0]:
        c.metric_link("Approved brand rules", approved, "in force for every audit", "forest", "constitution",
                      {"con_status": "Approved"}, "m1", "View approved rules", icon="rules")
    with m[1]:
        c.metric_link("Pending reviews", review, "rules unreviewed, flagged or with a potential finding", "warn" if review else "ok",
                      "constitution", {"con_status": "Needs review"}, "m2", "Review rules", icon="review")
    with m[2]:
        c.metric_link("Completed content audits", audits, "every revision is audited", "accent", "auditor",
                      {"aud_tab": "Drafts and submissions"}, "m3", "Open audits", icon="audit")
    with m[3]:
        c.metric_link("Unresolved conflicts", conflicts, "sources or rules that disagree", "alert" if conflicts else "ok",
                      "ruleprobe", {"probe_tab": "Conflicts"}, "m4", "Investigate", icon="conflict")
    st.write("")
    S_ = ga.summary(ws)
    left, right = st.container(key="pair-ovtop").columns([1.05, 1.25])
    with left:
        _health(ws, rules, conflicts)
    with right:
        _trends(S_)
    st.write("")
    a, b, d = st.container(key="pair-ovcards").columns(3)
    with a:
        _investigations(ws)
    with b:
        _audits(ws, S_)
    with d:
        _decisions(ws)
    st.write("")
    _attention(ws, user, S_)
