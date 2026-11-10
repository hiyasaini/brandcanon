"""Governance Intelligence — why brand inconsistencies keep happening. Every figure is computed from stored records."""
from collections import Counter
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from modules import governance_analytics as ga, queries as q, rule_probe
from ui import components as c
from ui import styles as S

ROOT_LABEL = {"Unresolved / other": "Unresolved issue", "Creator error": "Creator error", "Guideline defect": "Guideline defect",
              "Source conflict": "Source conflict", "Knowledge gap": "Knowledge gap"}
REC_ACTION = {  # recommendation title -> (button label, page, state)
    "Clarify a guideline": ("Open RuleProbe", "ruleprobe", {}),
    "Resolve conflicting source documents": ("Resolve conflicts", "ruleprobe", {"probe_tab": "Conflicts"}),
    "Update product specifications": ("Review product facts", "constitution", {"con_view": "Product facts"}),
    "Provide creator training": ("See the repeated errors", None, None),
    "Improve missing documentation": ("See missing guidance", "ruleprobe", {"probe_tab": "Missing guidance"}),
    "Review low-authority documents": ("Open document library", "constitution", {"con_tab": "Library"}),
}


FIX = [  # (heading, root causes counted, what it means, button label, page, state)
    ("Fix the people", ("Creator error",), "A clear, approved rule was broken. Brief or train the creators.",
     "Review creators' submissions", "auditor", {"aud_tab": "Drafts and submissions"}),
    ("Fix the rules", ("Guideline defect",), "The rule itself was unclear. Clarify it in RuleProbe.",
     "Open RuleProbe", "ruleprobe", {}),
    ("Fix the documents", ("Source conflict", "Knowledge gap"), "Sources disagree or say nothing. Resolve or add documents.",
     "Resolve conflicts", "ruleprobe", {"probe_tab": "Conflicts"}),
]


def _fix_where(rc):
    """The governance answer in one view: where should the brand team act — people, rules or documents?"""
    counts = [sum(rc.get(k, 0) for k in keys) for _, keys, *_ in FIX]
    total = sum(counts) or 1
    top = max(range(3), key=lambda i: counts[i]) if any(counts) else None
    st.markdown("#### Where to act")
    st.caption("Every first-draft finding in this period, grouped by what would have prevented it.")
    cols = st.container(key="pair-g1").columns(3)
    for i, (col, (head, keys, what, label, page, state)) in enumerate(zip(cols, FIX)):
        with col, c.card(key=f"card-fix{i}"):
            share = counts[i] / total
            st.markdown(f"<div class='bc-fix{' top' if i == top else ''}'><div class='h'>{head}</div>"
                        f"<div class='n'>{counts[i]}<span>{share:.0%} of findings</span>"
                        f"{'<em>largest share</em>' if i == top else ''}</div>"
                        f"<div class='bar'><i style='width:{share * 100:.0f}%'></i></div>"
                        f"<div class='w'>{c.esc(what)}</div><div class='bc-mono'>{c.esc(' + '.join(keys)).lower()}</div></div>",
                        unsafe_allow_html=True)
            if page and st.button(label, key=f"fixb{i}", type="tertiary", icon=":material/arrow_outward:", icon_position="right"):
                c.go(page, **state)


def render():
    ws, user = c.ctx()
    c.flash()
    c.page_head("Governance Intelligence", "Discover patterns behind recurring brand inconsistencies.")
    ws_row = next(w for w in q.list_workspaces() if w["id"] == ws)
    if ws_row["is_demo"]:
        c.illustrative()
        st.write("")
    with c.card():
        f1, f2, f3 = st.columns([1, 1, 1.2])
        start = f1.date_input("From", value=date.today() - timedelta(days=90), key="gov_from")
        end = f2.date_input("To", value=date.today(), key="gov_to")
        channel = f3.selectbox("Channel", ["All channels"] + [x for x in config.CHANNELS if x != "All content"], key="gov_ch")
    Sx = ga.summary(ws, start.isoformat(), end.isoformat(), channel)
    if not Sx["n_reports"]:
        c.empty("No audits in this period", "Audit content in the Content Auditor; governance analytics are computed from those "
                "stored audits and decisions.")
        return
    recurring = ga.recurring_violations(Sx)
    open_amb = [x for x in rule_probe.open_findings(ws) if x["test"]["classification"] == "Ambiguous rule"]
    mean_h, median_h, n_dec = ga.review_time_stats(ws)
    fmt = lambda h: "—" if h is None else (f"{h * 60:.0f} min" if h < 1 else f"{h:.1f} h")  # noqa: E731
    m = st.columns(4)
    with m[0]:
        c.metric("Recurring violations", len(recurring), "issues repeated across pieces of content", "forest", icon="repeat")
    with m[1]:
        c.metric_link("Unresolved ambiguities", len(open_amb), "potential findings not yet reviewed", "warn" if open_amb else "ok",
                      "ruleprobe", {"probe_rule": open_amb[0]["rule"]["id"]} if open_amb else {}, "g2", "Investigate", icon="probe")
    with m[2]:
        c.metric_link("Source conflicts", len(Sx["open_conflicts"]), "open, need a human decision",
                      "alert" if Sx["open_conflicts"] else "ok", "ruleprobe", {"probe_tab": "Conflicts"}, "g3", "Resolve", icon="conflict")
    with m[3]:
        c.metric_link("Average review time", fmt(mean_h),
                      f"revision to decision · median {fmt(median_h)} · {n_dec} decisions", "accent", "decisions",
                      {"dm_tab": "Approval history"}, "g4", "Review history", icon="time")
    st.write("")
    _fix_where(Sx["root_causes"])
    st.write("")

    first = Sx["first_findings"]
    a, b = st.container(key="pair-g3").columns([1.6, 1])
    with a, c.card(key="card-gtime"):
        c.card_title("Findings over time", "first drafts, per week")
        by = st.segmented_control("Break down by", ["Classification", "Root cause", "Severity"], default="Classification",
                                  key="gov_by", label_visibility="collapsed") or "Classification"
        field, palette, names = {
            "Classification": ("classification", S.CLASS_CHART, {}),
            "Root cause": ("root_cause", S.ROOT_CHART, ROOT_LABEL),
            "Severity": ("severity", {k: S.SEVERITY_CHART[k] for k in ("high", "medium", "low")},
                         {"high": "High", "medium": "Medium", "low": "Low"}),
        }[by]
        wf = {}
        for f in first:
            wf.setdefault(ga._week(f["report_at"]), Counter())[f[field]] += 1
        weeks = sorted(wf)
        palette = dict(palette)
        for cnt in wf.values():   # anything outside the named set is still counted, in neutral grey
            for k in cnt:
                palette.setdefault(k, S.CH_NEUTRAL)
        if weeks:
            totals = [sum(wf[w].values()) for w in weeks]
            peak = max(range(len(weeks)), key=lambda i: totals[i])
            keys, _ = c.week_ticks(weeks)
            st.markdown(c.chart_stat([(sum(totals), "first-draft findings"), (f"{sum(totals) / len(weeks):.1f}", "per week on average"),
                                      (totals[peak], f"at the peak, {keys[peak].split(' · ')[0]}")]), unsafe_allow_html=True)
            series = [(names.get(k, k), col, [wf[w].get(k, 0) for w in weeks]) for k, col in palette.items()]
            st.plotly_chart(c.weekly_bars(weeks, series, 270), width="stretch", config={"displayModeBar": False}, key="gov_time")
        else:
            st.caption("No findings in this period.")
    with b, c.card(key="card-gcat"):
        cats = Sx["categories"].most_common()
        total = sum(v for _, v in cats)
        c.card_title("Issue categories", f"{total} first-draft issues")
        if cats:
            top_n = cats[0][1]
            leaders = [k for k, v in cats if v == top_n]
            st.markdown(c.chart_stat([(f"{top_n / total:.0%}", f"of issues are {leaders[0].lower()}")] if len(leaders) == 1 else
                                     [(len(leaders), f"categories tie for most issues, {top_n} each")]), unsafe_allow_html=True)
            st.plotly_chart(c.hbars([k for k, _ in cats], [v for _, v in cats],
                                    [S.CH_GREEN if v == top_n else S.MINT for _, v in cats], total=total),
                            width="stretch", config={"displayModeBar": False}, key="gov_cat")
        else:
            st.caption("No issues recorded in this period.")

    a, b = st.container(key="pair-g4").columns([1, 1.15])
    with a, c.card(key="card-groot"):
        rc = Sx["root_causes"]
        labels = sorted(config.ROOT_CAUSES, key=lambda k: -rc.get(k, 0))
        c.card_title("Root cause analysis", "first drafts")
        st.plotly_chart(c.hbars([ROOT_LABEL.get(k, k) for k in labels], [rc.get(k, 0) for k in labels],
                                [S.ROOT_CHART[k] for k in labels]), width="stretch", config={"displayModeBar": False})
        st.caption("Counted on first drafts, so later fixes do not hide where problems started. Creator error: a clear rule was "
                   "broken. Guideline defect: the rule was unclear. Source conflict: documents disagree. Knowledge gap: no "
                   "approved evidence or rule exists.")
    with b, c.card(key="card-gchan"):
        c.card_title("Findings by channel", "first drafts, by severity")
        chans = Counter(f["channel"] for f in first)
        if chans:
            order = [k for k, _ in chans.most_common()]
            sev = {ch: Counter(f["severity"] for f in first if f["channel"] == ch) for ch in order}
            hi = max(order, key=lambda ch: sev[ch].get("high", 0))
            st.markdown(c.chart_stat([(len(order), "channels with findings"),
                                      (sev[hi].get("high", 0), f"high-severity in {hi}")]), unsafe_allow_html=True)
            fig = go.Figure()
            for k, nm in (("high", "High"), ("medium", "Medium"), ("low", "Low"), ("info", "Info")):
                vals = [sev[ch].get(k, 0) for ch in order]
                if any(vals):
                    fig.add_trace(go.Bar(y=order, x=vals, name=nm, orientation="h",
                                         marker=dict(color=S.SEVERITY_CHART[k], line=dict(color="#FFFFFF", width=1.5)),
                                         hovertemplate=f"%{{y}} · {nm}: <b>%{{x}}</b><extra></extra>"))
            tots = [sum(sev[ch].values()) for ch in order]
            fig.add_trace(go.Scatter(y=order, x=tots, mode="text", text=[f"  {t}" for t in tots], textposition="middle right",
                                     showlegend=False, hoverinfo="skip", cliponaxis=False,
                                     textfont=dict(size=11, color=S.TEXT)))
            fig.update_layout(barmode="stack", bargap=0.42)
            fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=12, color=S.TEXT))
            fig.update_xaxes(showticklabels=False, showline=False, range=[0, max(tots) * 1.15 + 0.5])
            st.plotly_chart(c.plot_layout(fig, 70 + 40 * len(order)), width="stretch", config={"displayModeBar": False},
                            key="gov_chan")
        else:
            st.caption("No findings in this period.")

    a, b = st.container(key="pair-g5").columns(2)
    with a, c.card(key="card-grules"):
        top = Sx["rules_broken"].most_common(6)
        c.card_title("Most frequently violated rules", f"{sum(Sx['rules_broken'].values())} violations")
        if top:
            rules = {r["code"]: r for r in q.list_rules(ws)}
            st.markdown(c.rank_rows([(c.code(k) + c.esc((rules.get(k) or {}).get("text", "")), v, (rules.get(k) or {}).get("text", k))
                                     for k, v in top], S.CH_CORAL), unsafe_allow_html=True)
        else:
            st.caption("No rule violations recorded in this period.")
    with b, c.card(key="card-gdec"):
        c.card_title("Reviewer decision trends", "per week")
        wa = Sx["weekly_approvals"]
        if wa:
            weeks = list(wa)
            all_dec = Counter()
            for w in weeks:
                all_dec.update(wa[w])
            n = sum(all_dec.values())
            stats = [(f"{all_dec.get('Approved', 0) / n:.0%}", f"approved · {all_dec.get('Approved', 0)} of {n} decisions")]
            if Sx["avg_revisions_to_approval"]:
                stats.append((Sx["avg_revisions_to_approval"], "revisions before approval, on average"))
            st.markdown(c.chart_stat(stats), unsafe_allow_html=True)
            series = [(k, col, [wa[w].get(k, 0) for w in weeks]) for k, col in S.DECISION_CHART.items()]
            series += [(k, S.CH_NEUTRAL, [wa[w].get(k, 0) for w in weeks]) for k in all_dec if k not in S.DECISION_CHART]
            st.plotly_chart(c.weekly_bars(weeks, series, 250, unit="decision"), width="stretch",
                            config={"displayModeBar": False}, key="gov_dec")
        else:
            st.caption("No review decisions yet.")

    a, b, cc = st.container(key="pair-g6").columns(3)
    with a, c.card(key="card-gterm"):
        c.card_title("Common terminology issues")
        terms = Sx["terminology"].most_common(6)
        if not terms:
            st.caption("No terminology violations recorded.")
        st.markdown(c.rank_rows([(f"“{c.esc(t)}”", n, t) for t, n in terms], S.CH_PURPLE), unsafe_allow_html=True)
    with b, c.card(key="card-gclaims"):
        c.card_title("Repeated unsupported claims")
        claims = ga.repeated_unsupported_claims(Sx)
        if not claims:
            st.caption("No unsupported claims recorded.")
        st.markdown(c.rank_rows([(f"“{c.esc(t[:70])}”", n, t) for t, n in claims[:6]], S.CH_AMBER), unsafe_allow_html=True)
    with cc, c.card(key="card-gamb"):
        c.card_title("Unresolved rule ambiguities", "how often two readings disagree")
        if not open_amb:
            st.caption("No open ambiguity findings.")
        amb = sorted(open_amb, key=lambda x: -x["test"]["divergence"])[:5]
        st.markdown(c.rank_rows([(c.code(x["rule"]["code"]) + c.esc(x["rule"]["text"]), f"{x['test']['divergence']:.0%}",
                                  x["rule"]["text"]) for x in amb], S.CH_PINK, values=[x["test"]["divergence"] for x in amb], scale=1),
                    unsafe_allow_html=True)
        if amb:
            st.caption("Investigate in RuleProbe:")
            with st.container(horizontal=True, gap="small"):
                for i, x in enumerate(amb):
                    if st.button(x["rule"]["code"], key=f"ua{i}", icon=":material/biotech:", help=x["rule"]["text"]):
                        c.go("ruleprobe", probe_rule=x["rule"]["id"])
            if len(open_amb) > len(amb):
                st.caption(f"{len(open_amb) - len(amb)} more in RuleProbe.")

    st.markdown("#### Recommended actions")
    recs = ga.recommendations(ws, Sx)
    if not recs:
        st.caption("No recommendations: no recurring problems found in this period.")
    cols = st.container(key="pair-g7").columns(2)
    for i, r in enumerate(recs):
        with cols[i % 2], c.card():
            st.markdown(f"{c.badge(ROOT_LABEL.get(r['root_cause'], r['root_cause']), 'terracotta')}"
                        f"<div class='bc-specimen-rule' style='font-size:1.3rem'>{c.esc(r['title'])}</div>"
                        f"<div style='font-size:.9rem'>{c.esc(r['detail'])}</div>", unsafe_allow_html=True)
            if r["evidence"]:
                st.markdown("<span class='bc-muted'>Based on: " + c.esc("; ".join(map(str, r["evidence"]))) + "</span>",
                            unsafe_allow_html=True)
            label, page, state = REC_ACTION.get(r["title"], (None, None, None))
            if page and st.button(label, key=f"rec{i}", type="tertiary", icon=":material/arrow_outward:", icon_position="right"):
                c.go(page, **state)
    with st.expander(f"All first-draft findings in this period · {len(first)} (the repeated errors behind creator training)"):
        df = pd.DataFrame([{"Date": f["report_at"][:10], "Content": f["title"], "Channel": f["channel"], "Category": f["category"],
                            "Classification": f["classification"], "Severity": f["severity"],
                            "Root cause": ROOT_LABEL.get(f["root_cause"], f["root_cause"]), "Quote": f["quote"],
                            "Rule": f["rule_code"] or ""} for f in first])
        st.dataframe(df, hide_index=True, width="stretch")
        st.download_button("Download CSV", df.to_csv(index=False), "brandcanon_findings.csv", icon=":material/download:")
