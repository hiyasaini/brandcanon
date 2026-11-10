"""Sign-in page — a separate, full-width page shown before the app (the sidebar is hidden here)."""
import time

import streamlit as st

from modules import auth, demo, queries as q
from ui import components as c, styles as S
from ui.components import esc

ss = st.session_state
MAX_ATTEMPTS = 5
LOCK_SECONDS = 60

CSS = f"""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarNav"],
[data-testid="stExpandSidebarButton"] {{ display: none !important; }}
[data-testid="stMainBlockContainer"], .block-container {{ max-width: 1240px; margin: 28px auto !important; padding: 34px 40px 40px !important;
    min-height: auto; }}
.bc-hero {{ padding: 6px 10px 0 0; display: flex; flex-direction: column; gap: 20px; }}
.bc-hero .brand {{ display: flex; align-items: center; gap: 12px; }}
.bc-hero .brand svg {{ width: 40px; height: 40px; }}
.bc-hero .brand .n {{ font-family: {S.DISPLAY}; font-weight: 800; font-size: 1.45rem; color: {S.TEXT}; line-height: 1; letter-spacing: -0.02em; }}
.bc-hero .brand .d {{ font-size: .64rem; letter-spacing: .1em; color: {S.MUTED}; font-weight: 700; margin-top: 4px; text-transform: uppercase; }}
.bc-hero h1 {{ font-family: {S.DISPLAY}; font-weight: 800; font-size: clamp(2.3rem, 3.8vw, 3.3rem); line-height: 1.04;
              letter-spacing: -0.035em; color: {S.TEXT}; margin: 4px 0 0; max-width: 15ch; }}
.bc-hero h1 em {{ font-style: normal; color: {S.GREEN}; }}
.bc-hero p.lede {{ color: {S.MUTED}; font-size: 1.02rem; line-height: 1.6; margin: 0; max-width: 52ch; }}
.bc-caps {{ display: flex; gap: 10px; flex-wrap: wrap; }}
.bc-cap {{ background: {S.SAGE_LIGHT}; border-radius: 14px; padding: 10px 14px; min-width: 150px; flex: 1; }}
.bc-cap b {{ display: block; font-family: {S.DISPLAY}; font-size: .92rem; color: {S.TEXT}; }}
.bc-cap span {{ font-size: .78rem; color: {S.MUTED}; }}
.bc-cap i {{ display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 6px; }}
.bc-exhibit {{ background: {S.DARK_BG}; border-radius: 20px; padding: 18px 20px 14px; max-width: 600px; color: {S.DARK_TEXT}; }}
.bc-exhibit .hd {{ display: flex; justify-content: space-between; font-family: {S.MONO}; font-size: .7rem; color: {S.DARK_MUTED}; }}
.bc-exhibit .copy {{ font-family: {S.DISPLAY}; font-weight: 600; font-size: 1.25rem; line-height: 1.45; color: #fff; margin: 10px 0 6px; }}
.bc-exhibit .ring {{ background: rgba(241,125,131,.18); box-shadow: inset 0 -2px 0 {S.CORAL}; border-radius: 4px; padding: 0 3px; }}
.bc-exhibit .bc-trail .node {{ background: #191B22; border-color: #2A2E37; }}
.bc-exhibit .bc-trail .node .v {{ color: {S.DARK_TEXT}; }}
.bc-exhibit .bc-trail .node .k {{ color: {S.DARK_MUTED}; }}
.bc-exhibit .bc-trail .link {{ border-top-color: #3A3F4B; }}
.bc-exhibit .verdict {{ display: flex; gap: 8px; align-items: baseline; font-size: .86rem; color: {S.DARK_TEXT}; margin-top: 8px; }}
.bc-exhibit .verdict .bc-muted {{ color: {S.DARK_MUTED}; }}
.bc-hero .foot {{ font-size: .76rem; color: {S.MUTED}; }}
.st-key-signin {{ background: {S.WHITE}; border: 1px solid {S.BORDER}; border-radius: 22px; padding: 24px 24px 18px;
                 box-shadow: 0 10px 30px rgba(16,28,22,.08); }}
.bc-login-title {{ font-family: {S.DISPLAY}; font-weight: 800; font-size: 1.8rem; color: {S.TEXT}; margin: 0 0 2px; letter-spacing: -0.02em; }}
.bc-login-sub {{ color: {S.MUTED}; font-size: .92rem; margin-bottom: 6px; }}
.bc-note {{ background: {S.YELLOW_TINT}; color: {S.YELLOW_TEXT}; border-radius: 12px; padding: 10px 12px; font-size: .84rem; line-height: 1.5; }}
.bc-note code {{ font-family: {S.MONO}; font-weight: 600; background: {S.WHITE}; color: {S.TEXT}; padding: 1px 5px; border-radius: 4px; }}
.bc-fine {{ color: {S.MUTED}; font-size: .76rem; line-height: 1.5; margin-top: 12px; }}
@media (max-width: 640px) {{ [data-testid="stMainBlockContainer"], .block-container {{ margin: 10px !important; padding: 18px 16px !important; }}
  .bc-exhibit, .bc-hero p.lede, .bc-caps {{ display: none; }} .bc-hero h1 {{ font-size: 2.1rem; }} }}
</style>
"""

ICON = ('<svg viewBox="0 0 34 34" aria-hidden="true"><rect x="1" y="1" width="32" height="32" rx="9" fill="#263A32"/>'
        '<path d="M12 12L23 10.5M12 12L22 22.5M12 12L11 23M22 22.5L11 23M23 10.5L22 22.5" stroke="#B9CDBD" stroke-width="1.1" '
        'stroke-opacity=".7"/><circle cx="12" cy="12" r="3" fill="#56C9C1"/><circle cx="23" cy="10.5" r="2.4" fill="#E79BD0"/>'
        '<circle cx="22" cy="22.5" r="3.2" fill="#B9CDBD"/><circle cx="11" cy="23" r="2.2" fill="#AD83EE"/></svg>')


def _locked():
    until = ss.get("login_lock_until", 0)
    if until > time.time():
        st.error(f"Too many incorrect attempts. Try again in {int(until - time.time()) + 1} seconds.", icon=":material/lock_clock:")
        return True
    return False


def _fail(msg):
    ss.login_fails = ss.get("login_fails", 0) + 1
    if ss.login_fails >= MAX_ATTEMPTS:
        ss.login_fails, ss.login_lock_until = 0, time.time() + LOCK_SECONDS
    st.error(msg, icon=":material/error:")


def _enter(user):
    ss.uid = user["id"]
    for k in ("login_fails", "login_lock_until", "cur_sub", "probe_rule", "probe_select"):
        ss.pop(k, None)
    st.rerun()


def _sign_in_tab():
    wss = q.list_workspaces()
    if not wss:
        st.info("No workspaces yet. Create one in the next tab.")
        return
    names = [w["name"] for w in wss]
    ws_name = st.selectbox("Brand workspace", names, key="login_ws")
    ws = wss[names.index(ws_name)]
    people = q.users(ws["id"])
    if not people:
        st.info("This workspace has no people yet.")
        return
    labels = {p["id"]: f"{p['name']} · {p['role']}" for p in people}
    uid = st.selectbox("Your name", list(labels), format_func=labels.get, key=f"login_user_{ws['id']}")
    if ws["is_demo"] and ss.get("tour"):
        st.markdown(f'<div class="bc-note"><b>Guided demo</b> — the next step is done as <b>{esc(labels.get(uid, ""))}</b>. '
                    f'Password <code>{auth.DEMO_PASSWORD}</code>.</div>', unsafe_allow_html=True)
    elif ws["is_demo"]:
        st.markdown(f'<div class="bc-note"><b>Demo workspace</b> — a fictional brand. Every demo person signs in with the '
                    f'password <code>{auth.DEMO_PASSWORD}</code>. Try Neha (Brand Manager), Kavya (Reviewer) or '
                    f'Priya (Creator).</div>', unsafe_allow_html=True)
    if not auth.has_password(uid):
        st.warning("This account was created before sign-in existed and has no password yet. Set one to activate it.",
                   icon=":material/key:")
        with st.form("activate"):
            p1 = st.text_input("New password", type="password")
            p2 = st.text_input("Repeat the password", type="password")
            if st.form_submit_button("Set password and sign in", type="primary", width="stretch"):
                try:
                    _enter(auth.activate(uid, p1, p2))
                except auth.AuthError as e:
                    st.error(str(e), icon=":material/error:")
        return
    with st.form("sign_in"):
        pw = st.text_input("Password", type="password", placeholder="Your password")
        go = st.form_submit_button("Sign in", type="primary", icon=":material/login:", width="stretch")
    if go and not _locked():
        try:
            _enter(auth.sign_in(uid, pw))
        except auth.AuthError as e:
            _fail(str(e))


def _create_tab():
    with st.form("create_ws"):
        brand = st.text_input("Brand or company name", placeholder="e.g. Acme Foods")
        me = st.text_input("Your name", placeholder="e.g. Asha")
        p1 = st.text_input("Password", type="password", help=f"At least {auth.MIN_LENGTH} characters.")
        p2 = st.text_input("Repeat the password", type="password")
        if st.form_submit_button("Create workspace", type="primary", icon=":material/add_business:", width="stretch"):
            try:
                _enter(auth.create_workspace(brand, me, p1, p2))
            except auth.AuthError as e:
                st.error(str(e), icon=":material/error:")
    st.markdown('<div class="bc-fine">You become the Brand Manager of the new workspace and can add reviewers and creators '
                'from Settings → Profile & people.</div>', unsafe_allow_html=True)


def render():
    st.markdown(CSS, unsafe_allow_html=True)
    if not q.list_workspaces():
        with st.spinner("Preparing the NovaTech demonstration workspace…"):
            demo.reset(with_history=True)
    left, gap, right = st.columns([1.15, 0.08, 0.85])
    with left:
        trail = c.evidence_trail([("Content", "“guarantees 15 hours”", ""), ("Rule", "Battery claims must match spec", ""),
                                  ("Source", "Product Specification v2.0 · p.3", ""), ("Evidence", "Up to 12 hours", "")])
        caps = "".join(f'<div class="bc-cap"><b><i style="background:{col}"></i>{t}</b><span>{d}</span></div>' for t, d, col in [
            ("RuleProbe", "Tests whether your guidelines are clear and consistent", S.TURQUOISE),
            ("Evidence Trail", "Every finding links to its rule, document and page", S.PINK),
            ("Decision Memory", "Past reviewer decisions inform new reviews", S.LAVENDER)])
        st.markdown(
            f'<div class="bc-hero"><div class="brand">{ICON}<div><div class="n">BrandCanon</div>'
            '<div class="d">Brand intelligence workspace</div></div></div>'
            '<h1>Every brand has rules. <em>We investigate whether they hold.</em></h1>'
            '<p class="lede">Upload your brand documents, test the rules for ambiguity and conflict, and audit content against '
            'approved evidence. Every finding cites its source, and people make every final decision.</p>'
            f'<div class="bc-caps">{caps}</div>'
            '<div class="bc-exhibit"><div class="hd"><span>EXHIBIT · Instagram caption</span><span>NovaTech (fictional)</span></div>'
            '<div class="copy">NovaTech <span class="ring">guarantees 15 hours</span> of battery life and will completely '
            'transform your productivity!</div>' + trail +
            f'<div class="verdict">{c.badge("Contradicted", "coral")}<span class="bc-muted">The specification says up to 12 hours, '
            'under specified testing conditions.</span></div></div>'
            f'<div class="foot">{esc(demo.DEMO_NAME)} is a fictional brand used for demonstration.</div></div>',
            unsafe_allow_html=True)
    with right, st.container(key="signin"):
        st.markdown('<div class="bc-login-title">Sign in</div>'
                    '<div class="bc-login-sub">Choose your brand workspace and your name, then enter your password.</div>',
                    unsafe_allow_html=True)
        t = st.tabs(["Sign in", "Create a workspace"])
        with t[0]:
            _sign_in_tab()
        with t[1]:
            _create_tab()
        st.markdown('<div class="bc-fine">Passwords are stored as salted PBKDF2 hashes in the local database. This is '
                    'prototype sign-in: there is no single sign-on, multi-factor authentication or password recovery.</div>',
                    unsafe_allow_html=True)
