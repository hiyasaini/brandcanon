"""Guided NovaTech demonstration — a slim stepper shown above every screen while the tour is on.

It walks through the Round 2 product story: knowledge → rule investigation → content audit → human decision → governance.
Each step is ticked from the records actually stored in the demo workspace (never from clicks), opens the right screen at the
right record, and says which demo person should do it. The tour only exists in the fictional demo workspace.
"""
import streamlit as st

from database import db
from modules import demo, queries as q
from ui import components as c

ss = st.session_state
TONE_RULE = "%friendly but professional%"


def _n(sql, ws):
    return db.fetch_one(sql, (ws,))["n"]


def _steps(ws):
    tone = db.fetch_one("SELECT id, rule_version FROM brand_rules WHERE workspace_id = ? AND text LIKE ? "
                        "AND status != 'Archived' ORDER BY id LIMIT 1", (ws, TONE_RULE))
    in_review = db.fetch_one("SELECT id FROM content_submissions WHERE workspace_id = ? AND status IN ('In review', 'Escalated') "
                             "ORDER BY updated_at DESC LIMIT 1", (ws,))
    approved_docs = _n("SELECT COUNT(*) n FROM documents WHERE workspace_id = ? AND review_status = 'Approved'", ws)
    resolved = _n("SELECT COUNT(*) n FROM source_conflicts WHERE workspace_id = ? AND status = 'resolved'", ws)
    # investigated = the tone rule was clarified, or its investigation was saved / sent / approved by a person
    investigated = bool(tone) and (tone["rule_version"] > 1 or db.fetch_one(
        "SELECT COUNT(*) n FROM rule_tests WHERE rule_id = ? AND investigation_state != 'draft'", (tone["id"],))["n"] > 0)
    submitted = _n("SELECT COUNT(*) n FROM content_submissions WHERE workspace_id = ? AND status != 'Draft'", ws)
    decided = _n("SELECT COUNT(*) n FROM decisions WHERE workspace_id = ?", ws)
    return [
        dict(k="Upload", title="Build the brand constitution", who="Neha",
             tip="Upload the NovaTech sample documents, then Approve pending at authority 3. Every rule keeps its page.",
             done=approved_docs > 0, page="constitution", state={"con_tab": "Upload"} if not approved_docs else {}),
        dict(k="Conflict", title="Resolve a source conflict", who="Neha",
             tip="The specification says 12 hours, the old presentation 15. Choose the source of truth and give a reason.",
             done=resolved > 0, page="ruleprobe", state={"probe_tab": "Conflicts"}),
        dict(k="Test rule", title="Investigate a vague rule", who="Neha",
             tip="Run tests on “friendly but professional”. Watch the strict and lenient readings split, then save version 2.",
             done=investigated, page="ruleprobe", state={"probe_rule": tone["id"]} if tone else {"probe_tab": "Investigation"}),
        dict(k="Audit", title="Audit a social post", who="Priya",
             tip="Submit the NovaTech example, open the source page behind a finding, Accept all, then Submit for approval.",
             done=submitted > 0, page="auditor", state={"aud_new": True, "ca_prefill": (demo.DEMO_POST, "NovaTech X1 battery post")}),
        dict(k="Approve", title="Decide with a rationale", who="Kavya",
             tip="Compare revisions, write a rationale and approve. The decision becomes a precedent for future reviews.",
             done=decided > 0, page="decisions", state={"dm_sub": in_review["id"]} if in_review else {}),
        dict(k="Insight", title="See where to act", who="Neha",
             tip="Governance shows whether to fix the people, the rules or the documents — each figure from stored records.",
             done=False, page="governance", state={}),
    ]


def _switch_to(name):
    """Sign out and pre-select the next demo person on the sign-in page (they still enter the password)."""
    ws_name, keep = ss.get("ws_name"), {"tour": True}
    keep.update({k: ss[k] for k in ("_db_path", "_db_token") if k in ss})   # public mode: keep this visitor's database
    people = {u["name"]: u["id"] for u in q.users(ss["ws"])}
    for k in list(ss.keys()):
        del ss[k]
    ss.update(keep)
    ss["login_ws"] = ws_name
    if name in people:
        ss[f"login_user_{_ws_id(ws_name)}"] = people[name]


def _ws_id(name):
    return next((w["id"] for w in q.list_workspaces() if w["name"] == name), None)


def bar(ws_row, me):
    if not (ss.get("tour") and ws_row["is_demo"]):
        return
    steps = _steps(ws_row["id"])
    cur = next((i for i, s in enumerate(steps) if not s["done"]), len(steps) - 1)
    s = steps[cur]
    chips = "".join(f'<div class="tr-chip {"done" if x["done"] else ("on" if i == cur else "")}"><b>{"✓" if x["done"] else i + 1}</b>'
                    f'{c.esc(x["k"])}</div>' + ('<div class="tr-line"></div>' if i < len(steps) - 1 else "")
                    for i, x in enumerate(steps))
    with st.container(key="tour"):
        st.markdown(f'<div class="tr-chips">{chips}</div><div class="tr-now"><span class="tr-step">Step {cur + 1} of '
                    f'{len(steps)}</span> <b>{c.esc(s["title"])}</b> · <span class="bc-muted">as {c.esc(s["who"])}</span>'
                    f'<div class="tr-tip">{c.esc(s["tip"])}</div></div>', unsafe_allow_html=True)
        with st.container(horizontal=True, gap="small"):
            if me["name"] != s["who"]:
                st.button(f"Sign in as {s['who']} for this step", key="tour_sw", type="primary", icon=":material/switch_account:",
                          on_click=_switch_to, args=(s["who"],))
            elif st.button("Take me there", key="tour_go", type="primary", icon=":material/arrow_forward:"):
                c.go(s["page"], **s["state"])
            if st.button("End guided demo", key="tour_end", type="tertiary", icon=":material/close:"):
                ss.pop("tour", None)
                st.rerun()


def _reset_and_start():
    me = ss.user
    ws = demo.reset(with_history=False)
    same = next((u for u in q.users(ws) if u["name"] == me["name"] and u["role"] == me["role"]), None)
    if same:
        ss.uid = same["id"]
    else:
        ss.pop("uid", None)
    for k in ("cur_sub", "probe_rule_id", "probe_select"):
        ss.pop(k, None)
    ss["tour"] = True
    ss["_flash"] = "Demo workspace emptied — the guided demo starts at step 1"


@st.dialog("Start the guided demo from an empty workspace?")
def _reset_dialog():
    st.markdown(f"This deletes everything in **{demo.DEMO_NAME}** (a fictional brand) and leaves it empty, so the demo starts "
                "with the first upload. Other workspaces are not touched. Demo people keep the password "
                f"`novatech-demo`.")
    a, b = st.columns(2)
    if a.button("Empty and start", type="primary", width="stretch"):
        with st.spinner("Preparing…"):
            _reset_and_start()
        st.rerun()
    if b.button("Cancel", width="stretch"):
        st.rerun()


def offer(ws_row):
    """On the Overview of the demo workspace: start the guided demo (optionally from an empty workspace)."""
    if not ws_row["is_demo"] or ss.get("tour"):
        return
    with st.container(key="tour-offer"):
        a, b = st.columns([3, 1.35], vertical_alignment="center")
        a.markdown("<div class='tr-offer'><b>Guided NovaTech demo</b> · six steps through the whole product — upload, "
                   "conflict, rule investigation, audit, human decision, governance. Each step is ticked from what is actually "
                   "stored.</div>", unsafe_allow_html=True)
        with b, st.container(horizontal=True, gap="small"):
            if st.button("Start", type="primary", icon=":material/play_circle:", key="tour_start"):
                ss["tour"] = True
                st.rerun()
            if st.button("Start from empty…", key="tour_reset", disabled=ss.user["role"] != "Brand Manager",
                         help="Brand Manager only: empties the demo workspace first (asks to confirm)."):
                _reset_dialog()
