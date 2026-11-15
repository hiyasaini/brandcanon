"""Accuracy benchmark screen: scores on hand-labelled items, per source, built-in vs Gemini, and one stored result per release."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from modules import benchmark, demo, evaluation, queries as q
from services import gemini_service as gs
from ui import components as c, styles as S

ss = st.session_state
TASKS = [("rules", "Ambiguity detection"), ("pairs", "Conflict detection"), ("claims", "Claim checking")]


def _demo_ws():
    return next((w["id"] for w in q.list_workspaces() if w["name"] == demo.DEMO_NAME), None)


def _tiles(res, prefix=""):
    cols = st.columns(3)
    for col, (k, title) in zip(cols, TASKS):
        m = res[k]["metrics"]
        with col:
            c.metric(prefix + title, f"F1 {m['f1']:.2f}", f"precision {m['precision']:.0%} · recall {m['recall']:.0%} · {len(res[k]['rows'])} items")


def _by_source(res):
    rows = []
    for src, per in res["by_source"].items():
        for k, title in TASKS:
            if per[k]["n"]:
                m = per[k]
                rows.append({"Source": src, "Check": title, "Items": m["n"], "Precision": m["precision"], "Recall": m["recall"], "F1": m["f1"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={x: st.column_config.NumberColumn(format="%.2f") for x in ("Precision", "Recall", "F1")})


def _history():
    runs = benchmark.runs()
    if not runs:
        return
    c.card_title("Release history", "one stored result per app version and engine")
    rows = [{"Version": r["app_version"], "Engine": r["engine"], "When": r["created_at"][:16].replace("T", " "),
             "Items": sum(r["item_counts"].values()),
             "Ambiguity F1": r["metrics"]["rules"]["f1"], "Conflict F1": r["metrics"]["pairs"]["f1"], "Claims F1": r["metrics"]["claims"]["f1"],
             "Gemini failures": r["metrics"].get("gemini_failed", 0)} for r in runs]
    st.dataframe(pd.DataFrame(rows[::-1]), hide_index=True, width="stretch")
    built = [r for r in runs if r["engine"] == "built-in"]
    latest = {}
    for r in built:
        latest[r["app_version"]] = r        # the newest built-in run of each version
    if len(latest) >= 2:
        vers = list(latest)
        fig = go.Figure()
        for key, title, col in (("rules", "Ambiguity", S.CH_GREEN), ("pairs", "Conflict", S.CH_CORAL), ("claims", "Claims", S.CH_PURPLE)):
            fig.add_trace(go.Scatter(x=vers, y=[latest[v]["metrics"][key]["f1"] for v in vers], mode="lines+markers", name=title,
                                     line=dict(width=2.5, color=col), marker=dict(size=8)))
        fig.update_yaxes(title="F1", range=[0, 1.05])
        st.plotly_chart(c.plot_layout(fig, 260), width="stretch", config={"displayModeBar": False})
    else:
        st.caption(f"Release {config.APP_VERSION} is the first stored result. Each later release adds a row here, so a change that "
                   "helps or hurts accuracy shows up as a line moving.")


def _import(ws, user):
    c.card_title("Add more labelled items", "from a real brand guideline you have labelled yourself")
    st.markdown("<span class='bc-muted'>Import a JSON file of hand-labelled items and say where they come from. They are scored "
                "separately from the built-in set. Claim items are checked against the approved facts of <b>this</b> workspace, so "
                "import them into the workspace that holds that brand's documents.</span>", unsafe_allow_html=True)
    st.download_button("Download the template", benchmark.template_json(), "benchmark_template.json", "application/json",
                       icon=":material/download:", key="bm_tpl")
    if user["role"] != "Brand Manager":
        st.caption("Only a Brand Manager can import or remove sets.")
        return
    up = st.file_uploader("Labelled set (JSON)", type=["json"], key="bm_up")
    if up and st.button("Import", type="primary", icon=":material/upload_file:", key="bm_imp"):
        n = c.run_action(benchmark.import_set, ws, user["id"], up.getvalue(), success="Labelled items imported")
        if n:
            ss.pop("bm_res", None)
            st.rerun()
    mine = benchmark.sets(ws)
    if mine:
        by_src = {}
        for s_ in mine:
            by_src[s_["source"]] = by_src.get(s_["source"], 0) + s_["item_count"]
        for src, n in by_src.items():
            a, b = st.columns([4, 1], vertical_alignment="center")
            a.markdown(f"**{c.esc(src)}** · {n} items", unsafe_allow_html=True)
            if b.button("Remove", key=f"bm_rm_{src}", icon=":material/delete:", width="stretch"):
                c.confirm(f"Remove “{src}”?", "Its items will no longer be scored. Stored release results are kept.", "Remove",
                          benchmark.delete_set, ws, user["id"], src, success="Set removed")


def render(ws, user):
    st.markdown("Scores BrandCanon's checks against hand-labelled items: **precision** is how many flags were right, **recall** is "
                "how many real problems were caught. Treat the numbers as measurements on these items, not as a promise about every brand.")
    demo_ws = _demo_ws()
    if not demo_ws:
        st.info("Load the demo workspace first; the built-in claim checks use NovaTech's specification.")
        return
    extra = benchmark.sets(ws)
    sig = tuple((e["id"]) for e in extra)
    if ss.get("bm_sig") != sig or "bm_res" not in ss:
        with st.spinner("Scoring the labelled items…"):
            ss["bm_res"] = evaluation.run_all(demo_ws, extra, False)
            ss["bm_sig"] = sig
            benchmark.ensure_current(demo_ws, ws)
    res = ss["bm_res"]
    n_all = sum(res["counts"].values())
    n_imp = sum(e["item_count"] for e in extra)
    pub = evaluation.public_info()
    n_pub = sum(len(x["items"]) for x in pub["sources"]) if pub else 0
    n_base = n_all - n_imp - n_pub
    st.markdown(f"<span class='bc-muted'>{n_all} labelled items · {n_pub} sentences from {len(pub['sources']) if pub else 0} real public "
                f"style guides · {n_base} written by the team for the fictional NovaTech brand · {n_imp} imported by you. "
                f"Release {config.APP_VERSION}.</span>", unsafe_allow_html=True)
    _tiles(res)
    c.card_title("By source", "each set scored on its own")
    _by_source(res)
    if pub:
        with st.expander("How the real-guideline items were labelled, and what the numbers say"):
            st.markdown(pub["note"])
            st.markdown(f"**Clear:** {pub['rubric']['clear']}  \n**Ambiguous:** {pub['rubric']['ambiguous']}")
            st.markdown("**Reading the result.** On the real guidelines the built-in check is precise (when it flags a rule, it is "
                        "usually right) but misses most ambiguous rules, because it only knows a fixed list of vague qualities. That "
                        "is the measured gap, and the reason live Gemini classification exists. Labels are a judgement call, so a "
                        "reviewer may disagree with some; the files are in `data/eval/`.")
    a, b = st.columns([1, 3], vertical_alignment="center")
    if a.button("Score again and store", icon=":material/refresh:", width="stretch", key="bm_again"):
        with st.spinner("Scoring…"):
            r2 = evaluation.run_all(demo_ws, extra, False)
            benchmark.store(ws, r2, "manual run")
            ss["bm_res"] = r2
        st.rerun()
    b.caption("Stores another result for this version.")

    c.card_title("Built-in logic vs live Gemini", "claim checking, same items, both engines")
    if not gs.enabled():
        st.caption("Needs live Gemini. It is not connected in this session, so only the built-in logic is scored.")
    elif st.button("Compare with live Gemini", type="primary", icon=":material/compare_arrows:", key="bm_cmp"):
        with st.spinner("Asking Gemini to check each labelled claim (this can take a minute)…"):
            g = evaluation.run_all(demo_ws, extra, True)
            benchmark.store(ws, g, "claim checks with live Gemini")
            ss["bm_gem"] = g
    g = ss.get("bm_gem")
    if g:
        if g["gemini_failed"]:
            st.error(f"Gemini did not answer for {g['gemini_failed']} of {len(g['claims']['rows'])} claims. Those are left out of "
                     "its score, not counted as answered. " + (gs.last_error() or ""), icon=":material/cloud_off:")
        mb, mg = res["claims"]["metrics"], g["claims"]["metrics"]
        st.dataframe(pd.DataFrame([
            {"Engine": "Built-in logic", "Precision": mb["precision"], "Recall": mb["recall"], "F1": mb["f1"], "Items scored": len(res["claims"]["rows"])},
            {"Engine": "Built-in + live Gemini", "Precision": mg["precision"], "Recall": mg["recall"], "F1": mg["f1"],
             "Items scored": len(g["claims"]["rows"]) - g["gemini_failed"]}]), hide_index=True, width="stretch")
    st.caption("Ambiguity and conflict detection are scored on the built-in logic: Gemini only proposes wording and test examples "
               "there, and the labelled items judge the logic itself.")

    _history()
    for k, title in TASKS:
        df = pd.DataFrame(res[k]["rows"])
        misses = df[df["pred"] != df["label"]]
        with st.expander(f"{title}: {len(misses)} miss(es)"):
            st.dataframe(df, hide_index=True, width="stretch")
    _import(ws, user)
