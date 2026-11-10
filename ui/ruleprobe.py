"""RuleProbe — test the logic behind your brand guidelines (dark investigation workspace).

Left: search and filter rules, choose the rule under examination, see related rules. Centre: the rule, its test cases
(generated, edited or added by hand), the strict-versus-lenient results and an investigation map
(Rule → Test case → Finding → Source document) whose nodes open their records. Right: the investigation details.
Bottom: the investigation actions. Every result is a potential finding until a person reviews it.
"""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from modules import ambiguity_detection as amb, conflict_detection, knowledge_graph as kg, queries as q, rule_probe
from ui import components as c
from ui import graph as kgui
from ui import styles as S

ss = st.session_state
TABS = ["Investigation", "Conflicts", "Missing guidance", "Test history"]
CLOSED = ("approved", "rule_updated")
VERDICT = lambda v: f"<span class='v-{v if v in ('pass', 'fail') else 'unclear'}'>{c.esc(v)}</span>"  # noqa: E731
ASSESS_CLASS = {"Likely compliant": "v-pass", "Potential violation": "v-fail", "Uncertain": "v-unclear",
                "Needs human review": "v-review"}
INV_TYPE = {"Ambiguous rule": "Ambiguity", "Contradictory rules": "Contradiction", "Missing guidance": "Missing guidance",
            "Model uncertainty": "Model uncertainty", "Clear rule": "No issue found"}
INV_TYPES = ["All investigation types", "Ambiguity", "Contradiction", "Missing guidance", "Model uncertainty", "No issue found",
             "Not tested"]
STATUSES = ["All approval statuses", "Approved", "Pending Validation", "Needs Clarification"]


def _cat(x):
    return config.DISPLAY_CATEGORY.get(x, x)


# ------------------------------------------------------------------ left: rule selection
def _rule_panel(ws, rules):
    latest = {}
    for t in q.all_tests(ws):          # ordered by id: the last one wins
        latest[t["rule_id"]] = t
    with c.card(key="panel-rulelist"):
        st.markdown("#### Rules")
        term = st.text_input("Search rules", key="probe_q", placeholder="Search rules or IDs", label_visibility="collapsed")
        cats = ["All categories"] + sorted({_cat(r["category"]) for r in rules})
        cat = st.selectbox("Rule category", cats, key="probe_cat")
        status = st.selectbox("Approval status", STATUSES, key="probe_status")
        itype = st.selectbox("Investigation type", INV_TYPES, key="probe_itype")

        def inv_of(r):
            t = latest.get(r["id"])
            return INV_TYPE.get(t["classification"], "Not tested") if t else "Not tested"
        view = [r for r in rules if (cat == "All categories" or _cat(r["category"]) == cat)
                and (status == "All approval statuses" or r["status"] == status)
                and (itype == "All investigation types" or inv_of(r) == itype)
                and (not term or term.lower() in f"{r['code']} {r['text']}".lower())]
        ids = [r["id"] for r in view]
        # keep the chosen rule even when its label changes (e.g. after a new version is saved)
        if ss.get("probe_rule_id") in ids:
            ss["probe_select"] = ss["probe_rule_id"]
        elif ss.get("probe_select") not in ids and view:
            ss["probe_select"] = view[0]["id"]
        if not view:
            c.empty("No rules match", "Change the filters.")
            return None
        by_id = {r["id"]: r for r in view}
        flag = {r["id"]: ("◆ " if r["clarity"] in ("Ambiguous", "In conflict", "Uncertain", "Missing guidance") else "")
                for r in view}
        st.caption(f"{len(view)} of {len(rules)} rules · ◆ earlier potential finding")
        with st.container(height=300, border=False):
            rid = st.radio("Rule", list(by_id), key="probe_select", label_visibility="collapsed",
                           on_change=lambda: ss.update(probe_rule_id=ss["probe_select"]),
                           format_func=lambda i: f"{flag[i]}{by_id[i]['code']} · {by_id[i]['text'][:46]}{'…' if len(by_id[i]['text']) > 46 else ''}")
        ss.setdefault("probe_rule_id", rid)
        r = by_id[rid]
        related = rule_probe.related_rules(ws, r)
        st.markdown(f"<div class='bc-muted' style='margin-top:6px'>Related rules · {len(related)}</div>", unsafe_allow_html=True)
        if not related:
            st.caption("No related rules found.")
        for x in related[:5]:
            st.markdown(f"<div style='font-size:.8rem;line-height:1.35;margin:4px 0'>{c.code(x['code'])} "
                        f"{c.esc(x['text'][:70])}</div>", unsafe_allow_html=True)
        return r


SHORT = {"pass": "✓", "fail": "✗"}


def _gauge(value, threshold):
    """Semicircle gauge for interpretation divergence, with the ambiguity threshold marked."""
    import math
    cx, cy, L = 80, 82, math.pi * 70
    tone = S.CORAL if value >= threshold else "#7FD3A0"
    th = math.pi * (1 - threshold)
    x1, y1 = cx + 60 * math.cos(th), cy - 60 * math.sin(th)
    x2, y2 = cx + 82 * math.cos(th), cy - 82 * math.sin(th)
    return (f'<svg viewBox="-14 -4 188 104" width="200" role="img" aria-label="Interpretation divergence {value:.0%}">'
            f'<path d="M10,82 A70,70 0 0 1 150,82" fill="none" stroke="#2A2E37" stroke-width="13" stroke-linecap="round"/>'
            f'<path d="M10,82 A70,70 0 0 1 150,82" fill="none" stroke="{tone}" stroke-width="13" stroke-linecap="round" '
            f'stroke-dasharray="{max(value, 0.001) * L:.1f} {L:.1f}" class="bc-gauge-arc"/>'
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{S.YELLOW}" stroke-width="1.8"/>'
            f'<text x="80" y="76" text-anchor="middle" font-family="Manrope, Inter, sans-serif" font-weight="800" '
            f'font-size="30" fill="#FFFFFF">{value:.0%}</text>'
            f'<text x="{x2 - 4:.1f}" y="{max(y2 - 7, 4):.1f}" text-anchor="end" font-size="8" fill="{S.DARK_MUTED}" '
            f'font-family="Inter, sans-serif">limit {threshold:.0%}</text></svg>')


def _split_view(t, cases):
    """The signature RuleProbe picture: the same examples judged by a strict and a lenient reading, side by side."""
    split = [i for i, x in enumerate(cases, 1) if x["strict_verdict"] != x["lenient_verdict"]]
    cols = ""
    for i, x in enumerate(cases, 1):
        d = ("Baseline" if x["dimension"] == "baseline" else "Your case" if x["dimension"] == "manual"
             else f"{amb.dim_label(x['dimension'])} {x['level']}")
        cell = lambda v: (f"<div class='sv-cell sv-{v if v in ('pass', 'fail') else 'unclear'}'>"  # noqa: E731
                          f"{SHORT.get(v, '?')}</div>")
        oc = S.OUTCOME.get(x["assessment"], S.OUTCOME["Uncertain"])[2]
        cols += (f"<div class='sv-col{' split' if i in split else ''}' title='{c.esc(x['example'])} — {c.esc(x['assessment'])}'>"
                 f"<div class='sv-n'>#{i}</div>{cell(x['strict_verdict'])}{cell(x['lenient_verdict'])}"
                 f"<div class='sv-d'><span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:{oc};"
                 f"margin-bottom:2px'></span><br>{c.esc(d)}</div></div>")
    th = rule_probe.AMBIGUITY_THRESHOLD
    if split:
        verdict = (f"The rule cannot decide case{'s' if len(split) > 1 else ''} "
                   f"{', '.join('#' + str(i) for i in split)}: one reading passes "
                   f"{'them' if len(split) > 1 else 'it'} and the other fails {'them' if len(split) > 1 else 'it'}.")
    else:
        verdict = "Both readings agree on every example — no ambiguity shown by this test."
    extra = (f"Repeated model runs disagreed on {t['self_inconsistency']:.0%} of examples."
             if t["engine"] and "gemini" in str(t["engine"]).lower() else "Deterministic logic gives the same answer every run.")
    return (f"<div class='bc-split'><div class='sv-gauge'>{_gauge(t['divergence'], th)}"
            f"<div class='sv-gl'>Interpretation divergence</div><div class='sv-gn'>{len(split)} of {len(cases)} examples split the "
            f"two readings</div></div><div class='sv-main'><div class='sv-grid'><div class='sv-legend'><div></div>"
            f"<div>Strict reading</div><div>Lenient reading</div><div></div></div>{cols}</div>"
            f"<div class='sv-verdict'>{c.esc(verdict)}</div><div class='bc-muted' style='font-size:.78rem'>{c.esc(extra)} "
            f"Hover a column to see its example.</div>{OUTCOME_LEGEND}</div></div>")


OUTCOME_LEGEND = ("<div style='display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:8px;font-size:.74rem'>" + "".join(
    f"<span style='display:inline-flex;align-items:center;gap:6px'><i style='width:9px;height:9px;border-radius:50%;"
    f"background:{v[2]};display:inline-block'></i>{k}</span>" for k, v in S.OUTCOME.items()) + "</div>")


# ------------------------------------------------------------------ centre: test laboratory
def _draft_key(rule, product):
    return f"draft_{rule['id']}_{rule['rule_version']}_{product}"


def _draft(ws, rule, product):
    k = _draft_key(rule, product)
    if k not in ss:
        ss[k] = [{"_id": i, "example": x["example"], "label": "Baseline" if x["dimension"] == "baseline"
                  else f"{amb.dim_label(x['dimension'])} · level {x['level']}", "_dim": x["dimension"], "_level": x["level"],
                  "_orig": x["example"]}
                 for i, x in enumerate(rule_probe.preview_cases(ws, rule["id"], product))]
        ss[k + "_n"] = len(ss[k])
    return ss[k]


def _cases_from(k, rows):
    """Read the case editor's widgets: an unchanged generated example keeps its dimension; anything edited or added is a
    manual case."""
    out = []
    for row in rows:
        if not ss.get(f"{k}_inc_{row['_id']}", True):
            continue
        text = str(ss.get(f"{k}_ex_{row['_id']}", row["example"]) or "").strip()
        if not text:
            continue
        same = row.get("_orig") is not None and row["_orig"].strip() == text
        out.append({"example": text, "dimension": row["_dim"] if same and row.get("_dim") else "manual",
                    "level": int(row["_level"]) if same and row.get("_level") is not None else 0})
    return out


def _case_editor(k, rows):
    st.markdown("<div class='bc-muted' style='margin:2px 0 6px'>Each generated example changes one characteristic. Edit any "
                "example or add your own; edited and added cases run as manual cases.</div>", unsafe_allow_html=True)
    for i, row in enumerate(rows):
        a, b, d, e = st.columns([0.35, 5, 1.7, 0.45], vertical_alignment="center")
        a.checkbox("Run", value=True, key=f"{k}_inc_{row['_id']}", label_visibility="collapsed")
        b.text_input(f"Case {i + 1}", value=row["example"], key=f"{k}_ex_{row['_id']}", label_visibility="collapsed",
                     max_chars=400)
        cur = ss.get(f"{k}_ex_{row['_id']}", row["example"])
        label = row["label"] if row.get("_orig") is not None and cur.strip() == row["_orig"].strip() else "Manual case"
        d.markdown(f"<span class='bc-mono'>{c.esc(label)}</span>", unsafe_allow_html=True)
        if e.button("", key=f"{k}_rm_{row['_id']}", icon=":material/close:", type="tertiary", help="Remove this case"):
            ss[k] = [x for x in rows if x["_id"] != row["_id"]]
            st.rerun()


def _lab(ws, user, rule):
    with c.card(key="panel-lab"):
        st.markdown(f'<div class="bc-specimen"><div class="code">{c.esc(rule["code"])} · version {rule["rule_version"]} · '
                    f'{c.esc(rule["scope"])} · {c.esc(rule["status"])}</div><div class="rule">{c.esc(rule["text"])}</div>'
                    f'</div>', unsafe_allow_html=True)
        st.write("")
        a, b = st.columns(2)
        context = a.selectbox("Context", config.CHANNELS, key="probe_ctx",
                              help="Where the rule will be applied. Rules scoped elsewhere show missing guidance here.")
        products = q.products(ws) or ["our product"]
        main = rule_probe.main_product(ws)
        product = b.selectbox("Product used in examples", products, index=products.index(main) if main in products else 0,
                              key="probe_prod")
        k = _draft_key(rule, product)
        rows = _draft(ws, rule, product)
        st.markdown("##### Test cases")
        if rows:
            _case_editor(k, rows)
        else:
            st.caption("This rule has no characteristic BrandCanon can vary on its own. "
                       + ("Live Gemini will propose examples for its undefined words, or add your own." if c.gs_enabled()
                          else "Add your own cases; without live Gemini they are marked Uncertain for you to judge."))
        can_run = user["role"] in ("Brand Manager", "Reviewer")
        cases = _cases_from(k, rows)
        bar = st.container(horizontal=True, gap="small")
        x = y = z = bar
        if x.button("Execute tests", type="primary", icon=":material/play_arrow:", disabled=not can_run, key="run"):
            with st.spinner("Evaluating each example under a strict and a lenient reading…"):
                tid = c.run_action(rule_probe.run_test, ws, user["id"], rule["id"], context, product,
                                   cases=cases or None)
            if tid:
                ss["_flash"] = "Test complete — results are potential findings until reviewed"
                st.rerun()
        if y.button("Add manual case", key="addcase", icon=":material/add:"):
            n = ss.get(k + "_n", len(rows)) + 1
            ss[k + "_n"] = n
            ss[k] = rows + [{"_id": 1000 + n, "example": "", "label": "Manual case", "_dim": None, "_level": None, "_orig": None}]
            st.rerun()
        if z.button("Generate test cases", key="reset", icon=":material/auto_awesome:",
                    help="Discard edits and regenerate the controlled examples for this rule."):
            for key in [x for x in ss.keys() if str(x).startswith(k)]:
                ss.pop(key, None)
            st.rerun()
        if not can_run:
            st.caption("Brand Managers and Reviewers can run tests.")
        _results(ws, user, rule)


def _results(ws, user, rule):
    tests = q.tests_for_rule(rule["id"])
    if not tests:
        st.write("")
        c.empty("No test yet", "Run the cases above. Each example is judged under a strict and a lenient reading of the rule.")
        return
    t = tests[0]
    cases = q.test_cases(t["id"])
    st.markdown("##### Test outcomes")
    dims = sorted({x["dimension"] for x in cases if x["dimension"] not in ("baseline", "manual")})
    if not cases:
        varied = "nothing to vary"
    else:
        varied = f"{', '.join(amb.dim_label(d) for d in dims) or 'manual cases'} · {len(cases)} example{'s' if len(cases) != 1 else ''}"
    st.markdown('<div class="bc-steps">'
                f'<div class="bc-step"><div class="t">Tested</div><div class="d">{rule["code"]} v{t["rule_version"]} · {c.esc(t["context"])}</div></div>'
                f'<div class="bc-step"><div class="t">Varied</div><div class="d">{c.esc(varied)}</div></div>'
                f'<div class="bc-step on"><div class="t">Potential finding</div><div class="d">{c.esc(t["classification"])}</div></div></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="bc-prov">Produced by ' + c.engine_tag(t["engine"]) + "</div>", unsafe_allow_html=True)
    c.engine_alert(t["engine"])
    if t["rule_version"] != rule["rule_version"]:
        st.info(f"These outcomes are for version {t['rule_version']}. The rule is now version {rule['rule_version']}; run the "
                "tests again to examine the new wording.", icon=":material/update:")
    if not cases:
        st.markdown(f"<div class='bc-split'><div class='sv-main'><div class='sv-verdict'>No examples were tested.</div>"
                    f"<div style='font-size:.9rem;margin:4px 0 8px'>{c.esc(t['issue'])}</div><div class='bc-muted'>Rules like "
                    "this are checked by exact matching in every audit. To see how people might read it, use <b>Add manual "
                    "case</b> and execute the tests again.</div></div></div>", unsafe_allow_html=True)
        _investigation_map(ws, rule)
        return
    st.markdown(_split_view(t, cases), unsafe_allow_html=True)
    rows = ""
    for i, x in enumerate(cases, 1):
        d = ("Baseline" if x["dimension"] == "baseline" else "Manual case" if x["dimension"] == "manual"
             else f"{amb.dim_label(x['dimension'])} · L{x['level']}")
        rows += (f"<tr class='{'hl' if x['strict_verdict'] != x['lenient_verdict'] else ''}'><td>{i}</td><td>{c.esc(x['example'])}"
                 f"<br><span class='bc-mono'>{c.esc(d)}</span></td><td>{VERDICT(x['strict_verdict'])}</td>"
                 f"<td>{VERDICT(x['lenient_verdict'])}</td><td><span class='{ASSESS_CLASS.get(x['assessment'], 'v-unclear')}'>"
                 f"{c.esc(x['assessment'])}</span><br><span class='bc-muted'>{x['confidence']} confidence</span></td>"
                 f"<td class='bc-muted'>{c.esc(x['reviewer_mark'] or '—')}</td></tr>")
    with st.expander(f"Case-by-case outcomes · {len(cases)} examples"):
        st.markdown("<table class='bc-table'><tr><th>#</th><th>Example</th><th>Strict</th><th>Lenient</th><th>Outcome</th>"
                    f"<th>Reviewer</th></tr>{rows}</table>", unsafe_allow_html=True)
        st.caption("Highlighted rows are where the two readings disagree.")
    _investigation_map(ws, rule)
    with st.expander("Explanations and reviewer marks"):
        marks = ["not reviewed", "correct", "incorrect", "inconclusive"]
        for i, x in enumerate(cases, 1):
            st.markdown(f"**{i}. {c.esc(x['example'])}**  \nStrict reading: {c.esc(x['strict_reason'])}  \n"
                        f"Lenient reading: {c.esc(x['lenient_reason'])}")
            if user["role"] in ("Brand Manager", "Reviewer"):
                cur = marks.index(x["reviewer_mark"]) if x["reviewer_mark"] else 0
                m_ = st.radio("Is this outcome right?", marks, index=cur, key=f"mk{x['id']}", horizontal=True,
                              label_visibility="collapsed")
                if m_ != marks[cur] and m_ != "not reviewed":
                    c.run_action(rule_probe.mark_case, ws, user["id"], x["id"], m_)


def _investigation_map(ws, rule):
    """Brand Rule → Test case → Finding → Source document, built from stored records. Clicking a node opens its record."""
    G = kg.build(ws)
    sub = kg.subgraph(G, ["document", "rule", "case", "finding"], ["contains", "tested_by", "produces", "contradicts",
                      "concerns", "supported_by"], focus=f"rule:{rule['id']}", depth=2)
    # keep the chain readable: this rule, its documents, its own cases and findings, and documents those findings cite
    keep = {f"rule:{rule['id']}"}
    for e in sub["edges"]:
        if e["source"] == f"rule:{rule['id']}" or e["target"] == f"rule:{rule['id']}":
            keep |= {e["source"], e["target"]}
    for e in sub["edges"]:
        if (e["source"] in keep and e["rel"] in ("produces", "supported_by", "contradicts")) or \
                (e["target"] in keep and e["rel"] == "produces"):
            keep |= {e["source"], e["target"]}
    sub = {"nodes": [n for n in sub["nodes"] if n["id"] in keep],
           "edges": [e for e in sub["edges"] if e["source"] in keep and e["target"] in keep]}
    st.markdown("##### Investigation map")
    st.markdown(kgui.legend_html({"document", "rule", "case", "finding"}) +
                "<div class='bc-muted' style='font-size:.78rem'>Brand rule → test cases → findings → source documents. "
                "Click a node to open its record.</div>", unsafe_allow_html=True)
    if len(sub["nodes"]) < 2:
        st.caption("Nothing connected yet — run the tests to link this rule to cases and findings.")
        return
    sel = kgui.chart(sub, f"probe_map_{rule['id']}", "hierarchical", 340, "key", compact=True)
    if sel:
        with c.card(key="panel-mapsel"):
            kgui.details(sub, sel, f"pm{rule['id']}")


# ------------------------------------------------------------------ right: investigation findings
def _findings(ws, user, rule):
    with c.card(key="panel-findings"):
        st.markdown("#### Investigation details")
        st.markdown(f"<div class='bc-mono'>Selected rule</div><div style='font-size:.9rem;margin-bottom:6px'>{c.code(rule['code'])} "
                    f"{c.esc(rule['text'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='bc-mono'>Source document</div><div style='font-size:.86rem;margin-bottom:8px'>"
                    f"{c.esc(rule['doc_title'] or 'Added manually')} {('· v' + c.esc(rule['doc_version']) + ' · ' + c.esc(rule['location'])) if rule['location'] else ''}"
                    f"</div>", unsafe_allow_html=True)
        tests = q.tests_for_rule(rule["id"])
        if not tests:
            st.markdown('<span class="bc-muted">No findings yet. Run the tests to examine this rule.</span>', unsafe_allow_html=True)
            return None
        t = tests[0]
        state = t["investigation_state"]
        cases = q.test_cases(t["id"])
        diverging = [i for i, x in enumerate(cases, 1) if x["strict_verdict"] != x["lenient_verdict"]]
        if t["classification"] == "Clear rule":
            st.markdown(f"{c.badge('No issue found', 'olive')}{c.badge(c.INVESTIGATION_LABEL.get(state, state))}", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:.9rem'>{c.esc(t['issue'])}</div>", unsafe_allow_html=True)
        else:
            sev = "high" if t["classification"] == "Contradictory rules" else "medium"
            st.markdown(f'<div class="bc-finding {sev}"><div class="tag">F-{t["id"]} · potential finding</div>'
                        f'<div class="phrase">{c.esc(t["classification"])}</div></div>', unsafe_allow_html=True)
            st.markdown(c.badge(c.INVESTIGATION_LABEL.get(state, state), "amber" if state not in CLOSED else "olive"),
                        unsafe_allow_html=True)
            st.markdown("**Explanation**")
            st.markdown(f"<div style='font-size:.9rem'>{c.esc(t['issue'])}</div>", unsafe_allow_html=True)
            if t["classification"] == "Model uncertainty":
                st.caption("Model uncertainty does not prove the rule is ambiguous; it may reflect missing context or model limits.")
            else:
                st.caption("A disagreement between readings is evidence for a person to weigh, not proof.")
            rel = [q.get_rule(i) for i in json.loads(t["related_rule_ids"] or "[]")]
            conf = q.open_conflicts_for_rule(rule["id"])
            st.markdown("**Related rules**")
            st.markdown(" ".join(c.code(x["code"]) for x in rel if x) or "<span class='bc-muted'>none</span>", unsafe_allow_html=True)
            if conf:
                for cf in conf:
                    st.markdown(f"{c.badge('Conflict', 'red')}<span style='font-size:.84rem'>{c.esc(cf['title'])}</span>",
                                unsafe_allow_html=True)
            st.markdown("**Relevant test cases**")
            st.markdown(("<span style='font-size:.88rem'>Readings disagree on cases " + ", ".join(f"#{i}" for i in diverging) + "</span>")
                        if diverging else "<span class='bc-muted'>Readings agree on every case.</span>", unsafe_allow_html=True)
            st.markdown("**Supporting source**")
            st.markdown(c.quote(rule["source_text"], f"{rule['doc_title']} · v{rule['doc_version']} · {rule['location'] or ''}"
                                if rule["location"] else ""), unsafe_allow_html=True)
            if t["recommendation"]:
                st.markdown("**Reasoning and suggested clarification**")
                st.markdown(f"<div style='font-size:.88rem'>{c.esc(t['recommendation'])}</div>", unsafe_allow_html=True)
        if t["notes"]:
            st.markdown(f"<div class='bc-precedent'><b>Reviewer note</b> · {c.esc(t['notes'])}</div>", unsafe_allow_html=True)
        if state in CLOSED:
            st.markdown(f"<span class='bc-muted'>Closed by {c.esc(t['resolved_by_name'] or '')} on {str(t['resolved_at'])[:10]}: "
                        f"{c.esc(t['resolution_note'] or '')}</span>", unsafe_allow_html=True)
        with st.expander("Investigation timeline"):
            st.markdown(c.timeline(rule_probe.timeline(t["id"])), unsafe_allow_html=True)
        return t


# ------------------------------------------------------------------ bottom: investigation actions
@st.dialog("Update rule after authorisation", width="large")
def _update_dialog(ws, user, rule, t):
    st.markdown("Saving creates **a new version** of the rule. The current wording stays in its history and earlier tests "
                "stay linked to the version they examined.")
    st.markdown(c.quote(rule["text"], f"{rule['code']} · current version {rule['rule_version']}"), unsafe_allow_html=True)
    text = st.text_area("Clarified rule", t["recommendation"] or rule["text"], height=110)
    why = st.text_input("Authorisation note (saved with the new version)", placeholder="e.g. Agreed with the brand team")
    if text.strip() != rule["text"].strip():
        st.markdown(c.diff(rule["text"], text), unsafe_allow_html=True)
    if st.button("Save version " + str(rule["rule_version"] + 1), type="primary", disabled=not why.strip()):
        ver = c.run_action(rule_probe.resolve_test, ws, user["id"], t["id"], "clarify", why, text)
        if ver:
            ss["_flash"] = f"{rule['code']} saved as version {ver}. Run the tests again to examine the new wording."
            st.rerun()


def _action_bar(ws, user, rule, t):
    with st.container(key="panel-actionbar"):
        closed = t["investigation_state"] in CLOSED or t["rule_version"] != rule["rule_version"]
        st.markdown("<div class='bc-mono' style='margin-bottom:4px'>Investigation actions</div>", unsafe_allow_html=True)
        note = st.text_input("Investigation note", key=f"note_{t['id']}", placeholder="Note for the record or the reviewer",
                             label_visibility="collapsed", disabled=closed)
        is_rev = user["role"] in ("Brand Manager", "Reviewer")
        is_bm = user["role"] == "Brand Manager"
        with st.container(horizontal=True, gap="small"):
            if st.button("Save investigation", key="ab_save", disabled=closed or not is_rev, icon=":material/save:"):
                if c.run_action(rule_probe.save_investigation, ws, user["id"], t["id"], note, success="Investigation saved"):
                    st.rerun()
            if st.button("Send for human review", key="ab_send", disabled=closed or not is_rev or t["investigation_state"] == "in_review",
                         icon=":material/send:"):
                if c.run_action(rule_probe.send_for_review, ws, user["id"], t["id"], note,
                                success="Sent to the Brand Manager for review"):
                    st.rerun()
            if st.button("Approve interpretation", key="ab_ok", disabled=closed or not is_bm,
                         icon=":material/verified:", help="The rule stays as written; this interpretation is accepted."):
                if c.run_action(rule_probe.resolve_test, ws, user["id"], t["id"], "keep",
                                note or "Interpretation approved as written", success="Interpretation approved"):
                    st.rerun()
            if st.button("Update rule after authorisation", key="ab_upd", disabled=closed or not is_bm,
                         type="primary", icon=":material/edit_note:"):
                _update_dialog(ws, user, rule, t)
    if not user["role"] == "Brand Manager":
        st.caption("Only a Brand Manager can approve an interpretation or update a rule. Reviewers can save and send for review.")


# ------------------------------------------------------------------ other tabs
def _conflicts_tab(ws, user):
    open_c = q.list_conflicts(ws, "open")
    st.markdown("<span class='bc-muted'>Where sources or rules disagree, BrandCanon records the conflict and shows both sides "
                "with their authority. It never picks a winner by itself.</span>", unsafe_allow_html=True)
    if not open_c:
        st.success("No open conflicts.", icon=":material/task_alt:")
    for cf in open_c:
        sides = q.conflict_sides(cf["id"])
        with c.card():
            st.markdown(f"{c.badge('Source conflict' if cf['kind'] == 'fact' else 'Rule conflict', 'red')}"
                        f"<b>{c.esc(cf['title'])}</b>", unsafe_allow_html=True)
            cols = st.columns(len(sides))
            for col, s in zip(cols, sides):
                with col:
                    head = f"{s['value']:g} {s['unit']}" if s["type"] == "fact" else f"{s['code']} · scope: {s['scope']}"
                    body = s["source_text"] if s["type"] == "fact" else s["text"]
                    st.markdown(f"<div class='bc-specimen-rule' style='font-size:1.25rem'>{c.esc(head)}</div>"
                                f"{c.badge(s['authority_level'] or 'Unknown authority', 'neutral')}"
                                f"{c.badge('authority ' + str(s['authority_rank']) + '/5', 'neutral')}{c.badge(s['status'])}"
                                + c.quote(body, f"{s['doc_title']} · v{s['doc_version']} · {s['location']}"), unsafe_allow_html=True)
            st.markdown(f"<span class='bc-muted'>{c.esc(cf['explanation'])}</span>", unsafe_allow_html=True)
            if user["role"] != "Brand Manager":
                st.caption("A Brand Manager resolves conflicts.")
                continue
            note = st.text_input("Reason for your decision", key=f"cn{cf['id']}")
            if cf["kind"] == "fact":
                opts = {f"{s['value']:g} {s['unit']} — {s['doc_title']} (v{s['doc_version']})": s["id"] for s in sides}
                keep = st.radio("Source of truth", list(opts), key=f"ck{cf['id']}", horizontal=True)
                if st.button("Resolve", key=f"cr{cf['id']}", type="primary", disabled=not note.strip()):
                    if c.run_action(conflict_detection.resolve_fact_conflict, ws, user["id"], cf["id"], opts[keep], note,
                                    success="Conflict resolved; the other value is now superseded"):
                        st.rerun()
            else:
                a_, b_ = sides[0], sides[1]
                acts = [f"Narrow the scope of {a_['code']}", f"Narrow the scope of {b_['code']}", f"Archive {a_['code']}",
                        f"Archive {b_['code']}", "Both can coexist"]
                act = st.selectbox("Resolution", acts, key=f"ca{cf['id']}")
                target = a_ if a_["code"] in act else b_
                scope = None
                if act.startswith("Narrow"):
                    scope = st.multiselect("New scope", [x for x in config.CHANNELS if x != "All content"], key=f"cs{cf['id']}")
                if st.button("Resolve", key=f"cr{cf['id']}", type="primary",
                             disabled=not note.strip() or (act.startswith("Narrow") and not scope)):
                    kind = "rescope" if act.startswith("Narrow") else ("archive" if act.startswith("Archive") else "compatible")
                    if c.run_action(conflict_detection.resolve_rule_conflict, ws, user["id"], cf["id"], kind, note,
                                    target["id"] if kind != "compatible" else None, ", ".join(scope or []) or None,
                                    success="Conflict resolved"):
                        st.rerun()
    done = q.list_conflicts(ws, "resolved")
    if done:
        with st.expander(f"Resolved conflicts · {len(done)}"):
            for cf in done:
                st.markdown(f"{c.badge('resolved')} **{c.esc(cf['title'])}** — {c.esc(cf['resolution'])}: {c.esc(cf['resolution_note'])} "
                            f"<span class='bc-mono'>{str(cf['resolved_at'])[:10]}</span>", unsafe_allow_html=True)


def _gaps_tab(ws):
    gaps = conflict_detection.coverage_gaps(ws)
    st.markdown("<span class='bc-muted'>Contexts where no rule is specifically scoped. Creators working here only have general "
                "rules to follow. BrandCanon reports the gap; it does not invent an official rule.</span>", unsafe_allow_html=True)
    if not gaps:
        st.success("Every listed context has at least one specific rule.")
        return
    st.markdown(" ".join(c.badge(g, "amber") for g in gaps), unsafe_allow_html=True)
    st.caption("To close a gap, add guidance to a source document and upload it, or confirm that general rules are enough.")


def _history_tab(ws):
    tests = q.all_tests(ws)
    if not tests:
        c.empty("No tests yet", "Run RuleProbe on a rule to start its test history.")
        return
    df = pd.DataFrame([{"When": t["created_at"][:16].replace("T", " "), "Rule": t["code"], "Version": t["rule_version"],
                        "Context": t["context"], "Potential finding": t["classification"], "Divergence": t["divergence"],
                        "Investigation": c.INVESTIGATION_LABEL.get(t["investigation_state"], t["investigation_state"]),
                        "Engine": t["engine"]} for t in tests])
    multi = df.groupby("Rule").filter(lambda g: g["Version"].nunique() > 1)
    if not multi.empty:
        fig = go.Figure()
        for code, g in multi.groupby("Rule"):
            fig.add_trace(go.Scatter(x=[f"v{v}" for v in g["Version"]], y=g["Divergence"] * 100, mode="lines+markers", name=code,
                                     line=dict(width=2)))
        fig.update_yaxes(title="divergence %", range=[0, 100])
        st.markdown("##### Divergence before and after clarification")
        st.plotly_chart(c.plot_layout(fig, 240, dark=True), width="stretch", config={"displayModeBar": False})
    rows = "".join(f"<tr><td class='bc-mono'>{c.esc(r['When'])}</td><td>{c.code(r['Rule'])} v{r['Version']}</td>"
                   f"<td>{c.esc(r['Context'])}</td><td>{c.esc(r['Potential finding'])}</td>"
                   f"<td><div class='bc-bar' style='height:7px;width:90px;display:inline-flex;background:#2A2E37'>"
                   f"<i style='width:{r['Divergence'] * 100:.0f}%;background:{S.CORAL if r['Divergence'] >= rule_probe.AMBIGUITY_THRESHOLD else S.TURQUOISE}'></i>"
                   f"</div> {r['Divergence']:.0%}</td><td>{c.esc(r['Investigation'])}</td></tr>"
                   for _, r in df.iloc[::-1].iterrows())
    st.markdown("<table class='bc-table'><tr><th>When</th><th>Rule</th><th>Context</th><th>Potential finding</th><th>Divergence</th>"
                f"<th>Investigation</th></tr>{rows}</table>", unsafe_allow_html=True)


def render():
    ws, user = c.ctx()
    S.dark()
    c.flash()
    if (rid := c.take("probe_rule")) is not None:
        ss["probe_select"], ss["probe_rule_id"], ss["probe_cat"], ss["probe_q"] = rid, rid, "All categories", ""
        ss["probe_status"], ss["probe_itype"] = "All approval statuses", "All investigation types"
        ss["probe_tab"] = "Investigation"

    def scan():
        res = c.run_action(rule_probe.scan, ws, user["id"])
        if res:
            ss["_flash"] = f"Tested {res[0]} rules · {res[1]} new conflicts recorded"
            st.rerun()
    c.page_head("RuleProbe", "Test the logic behind your brand guidelines.",
                [("Test all rules", scan, "secondary", ":material/radar:")] if user["role"] == "Brand Manager" else [])
    rules = q.list_rules(ws, ("Approved", "Pending Validation", "Needs Clarification"))
    if not rules:
        c.empty("No rules to examine", "Upload brand documents in Brand Constitution first.")
        return
    t = c.tabs(TABS, "probe_tabs", "probe_tab")
    with t[0]:
        cols3 = st.container(key="wrap-rp")
        left, mid, right = cols3.columns([0.95, 1.85, 1.1])
        with left, st.container(key="stick-rpl"):
            rule = _rule_panel(ws, rules)
        if not rule:
            return
        with mid:
            _lab(ws, user, rule)
        with right, st.container(key="stick-rpr"):
            test = _findings(ws, user, rule)
        if test:
            _action_bar(ws, user, rule, test)
    with t[1]:
        _conflicts_tab(ws, user)
    with t[2]:
        _gaps_tab(ws)
    with t[3]:
        _history_tab(ws)
