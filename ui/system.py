"""Settings: profile and people, AI status and data handling, accuracy evaluation, recorded test results, demo controls."""
import pandas as pd
import streamlit as st

import config
from modules import auth, demo, evaluation, queries as q
from services import gemini_service as gs
from ui import components as c


@st.dialog("Reset the demonstration workspace?")
def _reset_dialog():
    st.markdown(f"This deletes everything in **{demo.DEMO_NAME}** and rebuilds it from the sample documents. "
                "Other workspaces are not touched.")
    hist = st.toggle("Include example review history", value=True)
    st.caption("Everyone currently signed in to the demo workspace is signed out; you stay signed in if your name is one "
               "of the demo people.")
    if st.button("Reset demo", type="primary"):
        me = st.session_state.user
        with st.spinner("Rebuilding…"):
            ws = demo.reset(with_history=hist)
        same = next((u for u in q.users(ws) if u["name"] == me["name"] and u["role"] == me["role"]), None)
        if same:
            st.session_state.uid = same["id"]
        else:
            st.session_state.pop("uid", None)
        st.session_state.pop("cur_sub", None)
        st.session_state["_flash"] = "Demo workspace rebuilt"
        st.rerun()


def _ai_tab():
    s = gs.status()
    a, b = st.columns(2)
    with a, c.card():
        st.markdown("#### AI engine")
        rows = [("AI_PROVIDER", config.ai_provider()), ("GEMINI_MODEL", gs.model()),
                ("GEMINI_API_KEY", "configured (hidden)" if config.gemini_key() else "not set"),
                ("Mode", {"gemini": "Live Gemini selected", "deterministic": "Deterministic logic",
                          "misconfigured": "Gemini requested but not configured"}[s["mode"]])]
        info0 = gs.stats()
        if s["mode"] == "gemini":
            rows.append(("Verified", f"yes — last successful Gemini response {info0['last_success'].replace('T', ' ')}"
                         if info0["last_success"] else "not yet — press Test Gemini connection"))
        st.markdown("<table class='bc-table'>" + "".join(f"<tr><td><code>{k}</code></td><td>{c.esc(v)}</td></tr>" for k, v in rows)
                    + "</table>", unsafe_allow_html=True)
        if s["problem"]:
            st.error(s["problem"], icon=":material/error:")
        if s["mode"] == "gemini":
            st.markdown("Gemini is used for rule extraction and classification, RuleProbe examples (for undefined words) and "
                        "strict/lenient verdicts (3 passes each), clarification wording, a contextual tone/messaging/claim pass, "
                        "full-rewrite suggestions and precedent summaries. Every response is validated before it is used.")
        else:
            st.markdown("Every result comes from deterministic application logic and is labelled that way. To use live Gemini, "
                        "add to `.env`:")
            st.code("AI_PROVIDER=gemini\nGEMINI_API_KEY=your-key\nGEMINI_MODEL=gemini-3.5-flash-lite", language="bash")
            st.caption("Restart the app after editing .env.")
        st.write("")
        if st.button("Test Gemini connection", icon=":material/network_check:", disabled=s["mode"] != "gemini"):
            with st.spinner("Sending one short request to Gemini…"):
                st.session_state["_chk"] = gs.check_connection()
        chk = st.session_state.get("_chk") or gs.stats()["last_check"]
        if chk:
            if chk["ok"]:
                st.success(f"**Connected.** {chk['message']} Reply: “{chk['reply']}”", icon=":material/check_circle:")
            else:
                st.error(f"**Connection failed** ({chk.get('kind')}). {chk['message']}", icon=":material/cloud_off:")
                if chk.get("detail"):
                    st.caption(f"Technical detail (key removed): {chk['detail']}")
            st.caption(f"Checked at {chk['at'].replace('T', ' ')} · model {chk['model']}")
        info = gs.stats()
        st.caption(f"Since the app started: {info['live_calls']} live Gemini calls · {info['cache_hits']} cached responses reused · "
                   f"{info['failures']} failures.")
        err = gs.last_error_info()
        if err:
            st.warning(f"Most recent Gemini error ({err['at'].replace('T', ' ')} · {err['kind']}): {err['message']}",
                       icon=":material/warning:")
            if err["detail"]:
                st.caption(f"Technical detail (key removed): {err['detail']}")
    return b


def render():
    ws, user = c.ctx()
    c.flash()
    c.header([st.session_state.ws_name, "Settings"], "Settings",
             "Your profile and team, which AI is in use and what is sent to it, accuracy on a labelled set, and test results.")
    names = ["Profile & people", "AI and privacy", "Accuracy", "Test results", "Demo"]
    t = c.tabs(names, "set_tabs", "set_tab")
    with t[0]:
        _people_tab(ws, user)
    with t[1]:
        right = _ai_tab()
        with right, c.card():
            st.markdown("#### What happens to your data")
            st.markdown("- Documents, rules, audits and decisions are stored locally in SQLite.\n"
                        "- With live Gemini (AI_PROVIDER=gemini), the relevant document or content text is sent to Google’s Gemini API "
                        "after emails and phone numbers are removed. Google’s terms for your API key apply to that data.\n"
                        "- Uploaded text is wrapped as data; instructions inside documents are never followed and are flagged.\n"
                        "- Files are checked for type, size and signature before parsing.\n"
                        "- The API key is read from .env or Streamlit secrets, is never shown in the interface, and is removed "
                        "from every error message and log line.\n"
                        "- If a Gemini call fails, the result says so; nothing is presented as AI output that Gemini did not produce.\n"
                        "- Passwords are stored as salted PBKDF2 hashes.\n"
                        "- BrandCanon does not publish or reject content by itself; people make final decisions.\n"
                        "- This is an MVP: no enterprise authentication or compliance certification is claimed.")
    with t[2]:
        st.markdown("Scores on a small, hand-labelled set written by the team for the fictional NovaTech brand (deterministic engine). "
                    "Treat these as an early signal, not proof.")
        demo_ws = next((w["id"] for w in q.list_workspaces() if w["name"] == demo.DEMO_NAME), None)
        if not demo_ws:
            st.info("Load the demo workspace first; the claim checks use NovaTech's specification.")
        elif st.button("Run evaluation", icon=":material/play_arrow:") or "eval" in st.session_state:
            E = st.session_state["eval"] = st.session_state.get("eval") or evaluation.run(demo_ws)
            cols = st.columns(3)
            for col, (k, title) in zip(cols, [("rules", "Ambiguity detection"), ("pairs", "Conflict detection"), ("claims", "Claim checking")]):
                m = E[k]["metrics"]
                with col:
                    c.metric(title, f"F1 {m['f1']:.2f}", f"precision {m['precision']:.0%} · recall {m['recall']:.0%} · {len(E[k]['rows'])} items")
            for k, title in [("rules", "Ambiguity detection"), ("pairs", "Conflict detection"), ("claims", "Claim checking")]:
                df = pd.DataFrame(E[k]["rows"])
                misses = df[df["pred"] != df["label"]]
                with st.expander(f"{title}: {len(misses)} miss(es)"):
                    st.dataframe(df, hide_index=True, width="stretch")
    with t[3]:
        p = config.ROOT / "docs" / "test_results.txt"
        if p.exists():
            st.markdown("Output of the last `pytest` run, saved by `scripts/run_tests.sh`:")
            st.code(p.read_text()[-6000:], language="text")
        else:
            st.info("No recorded test run yet. Run `bash scripts/run_tests.sh`.")
    with t[4]:
        st.markdown(f"The **{demo.DEMO_NAME}** workspace uses a fictional brand. Its review history is created through the real "
                    "pipeline and backdated so trends are visible; it is not customer activity.")
        if st.button("Reset demo workspace…", icon=":material/restart_alt:"):
            _reset_dialog()


def _people_tab(ws, user):
    people = q.users(ws)
    st.markdown("<table class='bc-table'><tr><th>Name</th><th>Role</th><th>Sign-in</th></tr>" + "".join(
        f"<tr><td>{c.esc(p['name'])}</td><td>{c.esc(p['role'])}</td>"
        f"<td>{'password set' if p.get('password_hash') else 'not activated'}</td></tr>" for p in people) + "</table>",
                unsafe_allow_html=True)
    st.write("")
    a, b = st.columns(2)
    with a, c.card():
        st.markdown("#### Add a person")
        if user["role"] != "Brand Manager":
            st.caption("Only a Brand Manager can add people or reset passwords.")
        else:
            with st.form("add_person", clear_on_submit=True):
                n = st.text_input("Name")
                r = st.selectbox("Role", ["Creator", "Reviewer", "Brand Manager"])
                pw = st.text_input("Initial password", type="password", help=f"At least {auth.MIN_LENGTH} characters. "
                                   "Share it with the person privately.")
                if st.form_submit_button("Add person", type="primary"):
                    if c.run_action(auth.add_person, ws, user["id"], n, r, pw, success=f"{n} added as {r}"):
                        st.rerun()
            with st.expander("Reset someone's password"):
                others = [p for p in people if p["id"] != user["id"]]
                if others:
                    pid = st.selectbox("Person", [p["id"] for p in others],
                                       format_func=lambda i: next(f"{p['name']} · {p['role']}" for p in others if p["id"] == i))
                    npw = st.text_input("New password", type="password", key="reset_pw")
                    if st.button("Reset password", disabled=not npw):
                        c.run_action(auth.reset_password, ws, user["id"], pid, npw, success="Password reset")
    with b, c.card():
        st.markdown("#### Change your password")
        with st.form("change_pw", clear_on_submit=True):
            cur = st.text_input("Current password", type="password")
            n1 = st.text_input("New password", type="password")
            n2 = st.text_input("Repeat the new password", type="password")
            if st.form_submit_button("Change password"):
                c.run_action(auth.change_password, user["id"], cur, n1, n2, success="Password changed")
