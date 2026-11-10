"""BrandCanon — brand intelligence workspace.  Run: streamlit run app.py"""
import re
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="BrandCanon · Brand Intelligence", page_icon="assets/logo/icon.svg", layout="wide",
                   initial_sidebar_state="expanded")

import config  # noqa: E402
from database import db  # noqa: E402
from modules import demo, notifications, queries as q  # noqa: E402
from services import gemini_service as gs  # noqa: E402
from ui import (constitution, content_auditor, dashboard, decision_memory, governance, graph, help as help_page,  # noqa: E402
                login, ruleprobe, search, styles, system, tour)
from ui import components as c  # noqa: E402
from ui.components import esc  # noqa: E402

ss = st.session_state


@st.cache_resource(show_spinner="Preparing the NovaTech demonstration workspace…")
def _template_db():
    """Public mode: build the demo once per server; every visitor then gets a copy of it."""
    path = Path(tempfile.gettempdir()) / "brandcanon_template.db"
    for f in path.parent.glob(path.name + "*"):
        f.unlink()
    ss["_db_path"] = str(path)
    db.reset_connections()
    db.init()
    demo.reset(with_history=True)
    db.conn().execute("PRAGMA wal_checkpoint(TRUNCATE)")
    ss.pop("_db_path", None)
    return str(path)


def _session_db():
    """A private database for this visitor, kept across page reloads through a random token in the link."""
    token = st.query_params.get("s", "")
    if not re.fullmatch(r"[0-9a-f]{32}", token or ""):
        token = uuid.uuid4().hex
    path = Path(tempfile.gettempdir()) / f"brandcanon_s_{token}.db"
    if not path.exists():
        cutoff = time.time() - 24 * 3600   # tidy copies nobody has used for a day
        for old in path.parent.glob("brandcanon_s_*.db*"):
            if old.stat().st_mtime < cutoff:
                old.unlink(missing_ok=True)
        src, dst = sqlite3.connect(_template_db()), sqlite3.connect(path)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
    return token, str(path)


if config.public_mode():
    if "_db_path" not in ss or not Path(ss["_db_path"]).exists():
        ss["_db_token"], ss["_db_path"] = _session_db()
    if st.query_params.get("s") != ss["_db_token"]:
        st.query_params["s"] = ss["_db_token"]

try:
    db.init()
except db.DatabaseError as e:
    st.error(str(e))
    st.stop()

if not q.list_workspaces():
    with st.spinner("Preparing the NovaTech demonstration workspace…"):
        demo.reset(with_history=True)

styles.inject()
c.reset_cards()

PAGES = [  # (url_path, title, icon, render)
    ("overview", "Overview", ":material/space_dashboard:", dashboard.render),
    ("constitution", "Brand Constitution", ":material/menu_book:", constitution.render),
    ("ruleprobe", "RuleProbe", ":material/biotech:", ruleprobe.render),
    ("auditor", "Content Auditor", ":material/plagiarism:", content_auditor.render),
    ("decisions", "Decision Memory", ":material/history_edu:", decision_memory.render),
    ("governance", "Governance Intelligence", ":material/query_stats:", governance.render),
    ("graph", "Knowledge Graph", ":material/hub:", graph.render),
]
SETTINGS = [
    ("settings", "Settings", ":material/tune:", system.render),
    ("help", "Help & documentation", ":material/help:", help_page.render),
]
HIDDEN = [("search", "Search", ":material/search:", search.render)]

# ---------------------------------------------------------------- sign-in gate (separate page, no sidebar)
me = q.user(ss.get("uid")) if ss.get("uid") else None
if not me:
    ss.pop("uid", None)
    # Every app URL shows the sign-in page until someone signs in; afterwards the requested page opens.
    gate = [st.Page(login.render, title="Sign in", icon=":material/login:", url_path="login", default=True)]
    gate += [st.Page(login.render, title=f"Sign in · {t}", url_path=u) for u, t, _, _ in PAGES + SETTINGS + HIDDEN]
    st.navigation(gate, position="hidden").run()
    st.stop()

ws_row = next(w for w in q.list_workspaces() if w["id"] == me["workspace_id"])
ss.ws, ss.ws_name = ws_row["id"], ws_row["name"]
ss.user = {k: v for k, v in me.items() if k != "password_hash"}

pages = [st.Page(fn, title=t, icon=i, url_path=u, default=(u == "overview")) for u, t, i, fn in PAGES + SETTINGS + HIDDEN]
ss.pages = {p.url_path: p for p in pages}
current = st.navigation(pages, position="hidden")

ICON = ('<svg viewBox="0 0 34 34" aria-hidden="true"><rect x="1" y="1" width="32" height="32" rx="9" fill="#263A32"/>'
        '<path d="M12 12L23 10.5M12 12L22 22.5M12 12L11 23M22 22.5L11 23M23 10.5L22 22.5" stroke="#B9CDBD" stroke-width="1.1" '
        'stroke-opacity=".7"/><circle cx="12" cy="12" r="3" fill="#56C9C1"/><circle cx="23" cy="10.5" r="2.4" fill="#E79BD0"/>'
        '<circle cx="22" cy="22.5" r="3.2" fill="#B9CDBD"/><circle cx="11" cy="23" r="2.2" fill="#AD83EE"/></svg>')


def _sign_out():
    keep = {"tour": True} if ss.get("tour") else {}   # the guided demo continues after switching person
    keep.update({k: ss[k] for k in ("_db_path", "_db_token") if k in ss})   # public mode: keep this visitor's database
    for k in list(ss.keys()):
        del ss[k]
    ss.update(keep)


def _switch_workspace():
    """Accounts belong to a workspace, so switching means signing in to the other one."""
    target = ss.get("ws_switch")
    if target and target != ws_row["name"]:
        _sign_out()
        ss["login_ws"] = target


def _search():
    # a text box can re-send an unchanged value when it loses focus (e.g. clicking a result); only a new query navigates
    q_ = (ss.get("gsearch") or "").strip()
    if q_ and q_ != ss.get("search_q"):
        ss["search_q"] = q_
        ss["_search_go"] = True


def _ai_card(demo_brand):
    """The sidebar's engine card: one HTML block so the dot, status, model and demo label always line up."""
    s = gs.status()
    sub, err_html = "", ""
    if s["mode"] == "gemini":
        info = gs.stats()
        if gs.checking():
            color, text = styles.YELLOW, "Gemini · checking the connection…"
        elif (info["last_check"] or {}).get("ok"):
            color, text = styles.MINT, "Live Gemini · verified"
        elif info["last_success"]:
            color, text = styles.MINT, "Live Gemini · working"
        elif info["last_check"]:
            color, text = styles.CORAL, "Gemini selected · connection failed"
        else:
            color, text = styles.YELLOW, "Gemini selected · not yet verified"
        sub = gs.model()
        if info["last_check"] and not info["last_check"].get("ok") and not info["last_success"] and not gs.checking():
            sub = f"{gs.model()} · {info['last_check'].get('message', '')[:90]} Retrying automatically."
    elif s["mode"] == "misconfigured":
        color, text, sub = styles.CORAL, "Gemini not configured", "Results use deterministic logic."
    else:
        color, text, sub = "#C9D3CC", "Deterministic logic", "Live Gemini is off (AI_PROVIDER)."
    err = gs.last_error_info()
    failed_check = s["mode"] == "gemini" and (gs.stats()["last_check"] or {}).get("ok") is False and not gs.stats()["last_success"]
    if err and s["mode"] != "deterministic" and not failed_check:
        err_html = (f"<div class='bc-ai-row err'><i style='background:{styles.CORAL}'></i><div><b>Last Gemini error at "
                    f"{esc(err['at'][11:16])}</b><span>{esc(err['message'][:90])}</span></div></div>")
    st.markdown(f"<div class='bc-ai'><div class='bc-side-t'>AI engine</div>"
                f"<div class='bc-ai-row'><i style='background:{color}'></i><div><b>{esc(text)}</b>"
                f"{f'<span>{esc(sub)}</span>' if sub else ''}</div></div>{err_html}"
                f"{'<span class=bc-demo>Illustrative demo brand</span>' if demo_brand else ''}</div>", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def _auto_verify(_slot):
    """One automatic live check per server process (and again at most every 2 minutes while it keeps failing)."""
    return gs.verify_in_background()


if gs.status()["mode"] == "gemini" and not (gs.stats()["last_check"] or {}).get("ok") and not gs.checking():
    _auto_verify(int(time.time() // 120) if gs.stats()["last_check"] else 0)


def _ai_card_live():
    _ai_card(ws_row["is_demo"])
    if not gs.checking() and ss.pop("_ai_was_checking", False):
        st.rerun()   # the check finished: refresh once so every screen sees the verified engine
    if gs.checking():
        ss["_ai_was_checking"] = True


# ---------------------------------------------------------------- left sidebar: navigation only
with st.sidebar:
    st.markdown('<div class="bc-navlabel">Workspace</div>', unsafe_allow_html=True)
    st.page_link(pages[0], label=pages[0].title, icon=pages[0].icon, width="stretch")
    st.markdown('<div class="bc-navlabel">Investigate</div>', unsafe_allow_html=True)
    for p in pages[1:len(PAGES)]:
        st.page_link(p, label=p.title, icon=p.icon, width="stretch")
    st.markdown('<div class="bc-navlabel">Support</div>', unsafe_allow_html=True)
    for p in pages[len(PAGES):len(PAGES) + len(SETTINGS)]:
        st.page_link(p, label=p.title, icon=p.icon, width="stretch")
    with st.container(key="side-foot"):
        initials_ = "".join(w[0] for w in me["name"].split()[:2]).upper()
        st.markdown(f"<div class='bc-side-me'><div class='bc-avatar'>{esc(initials_)}</div><div><div class='n'>{esc(me['name'])}"
                    f"</div><div class='r'>{esc(me['role'])} · {esc(ws_row['name'])}</div></div></div>", unsafe_allow_html=True)
        st.fragment(_ai_card_live, run_every="2s" if gs.checking() else None)()


# ---------------------------------------------------------------- top bar: brand, workspace, search, notifications, profile
def topbar():
    with st.container(key="topbar"):
        cols = st.columns([1.45, 1.35, 2.2, 0.95, 1.2], vertical_alignment="center", gap="small")
        cols[0].markdown(f'<div class="bc-brand">{ICON}<div><div class="name">BrandCanon</div>'
                         f'<div class="desc">Brand intelligence</div></div></div>', unsafe_allow_html=True)
        names = [w["name"] for w in q.list_workspaces()]
        cols[1].selectbox("Workspace", names, index=names.index(ws_row["name"]), key="ws_switch", on_change=_switch_workspace,
                          label_visibility="collapsed", help="Each workspace has its own people. Choosing another one "
                          "takes you to its sign-in.")
        cols[2].text_input("Search", key="gsearch", on_change=_search, label_visibility="collapsed",
                           placeholder="Search rules, documents, claims, decisions…  (press Enter)")
        items = notifications.for_user(ws_row["id"], ss.user)
        if ss.pop("_close_pop", False):
            ss["notif_pop"] = False
        with cols[3].popover(str(len(items)) if items else "", icon=":material/notifications:", key="notif_pop",
                             on_change="rerun", help="Notifications", width="stretch"):
            st.markdown("**Notifications**")
            if not items:
                st.caption("Nothing needs your attention right now.")
            for i, it in enumerate(items[:12]):
                st.markdown(f"**{esc(it['title'])}**  \n<span class='bc-muted'>{esc(it['detail'])}</span>", unsafe_allow_html=True)
                if st.button("Open", key=f"nt{i}", type="tertiary", icon=":material/arrow_outward:", icon_position="right"):
                    c.go(it["page"], _close_pop=True, **it["state"])
        initials = "".join(w[0] for w in me["name"].split()[:2]).upper()
        if ss.pop("_close_prof", False):
            ss["prof_pop"] = False
        with cols[4].popover(me["name"], icon=":material/account_circle:", width="stretch", key="prof_pop", on_change="rerun"):
            st.markdown(f'<div class="bc-profile"><div class="bc-avatar">{esc(initials)}</div><div><div class="n">'
                        f'{esc(me["name"])}</div><div class="r">{esc(me["role"])} · {esc(ws_row["name"])}</div></div></div>',
                        unsafe_allow_html=True)
            if st.button("Profile", icon=":material/person:", type="tertiary", key="tb_prof"):
                c.go("settings", set_tab="Profile & people", _close_prof=True)
            if st.button("Settings", icon=":material/tune:", type="tertiary", key="tb_set"):
                c.go("settings", _close_prof=True)
            st.button("Sign out", icon=":material/logout:", on_click=_sign_out, type="tertiary", key="tb_out")


topbar()
if ss.pop("_search_go", False):
    c.go("search")
tour.bar(ws_row, me)
current.run()
