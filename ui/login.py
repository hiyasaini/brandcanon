"""Sign-in page — a separate, full-width page shown before the app (the sidebar is hidden here)."""
import time

import streamlit as st

import config
from modules import auth, demo, queries as q, session_token
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
.st-key-signin [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
.st-key-signin {{ padding-bottom: 26px !important; }}
@media (max-width: 640px) {{ [data-testid="stMainBlockContainer"], .block-container {{ margin: 10px !important; padding: 18px 16px !important; }}
  .bc-exhibit, .bc-hero p.lede, .bc-caps {{ display: none; }} .bc-hero h1 {{ font-size: 2.1rem; }} }}
/* ---- motion: small, quick, once. Switched off for people who ask their device for reduced motion. */
@keyframes bc-rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes bc-slide {{ from {{ opacity: 0; transform: translateX(22px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes bc-pop {{ 0% {{ opacity: 0; transform: scale(.6); }} 70% {{ transform: scale(1.08); }} 100% {{ opacity: 1; transform: none; }} }}
@keyframes bc-draw {{ to {{ stroke-dashoffset: 0; }} }}
@keyframes bc-grow {{ from {{ width: var(--from, 0%); }} }}
@keyframes bc-fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
.bc-hero .brand {{ animation: bc-rise .55s ease both; }}
.bc-hero h1 {{ animation: bc-rise .55s .08s ease both; }}
.bc-hero p.lede {{ animation: bc-rise .55s .16s ease both; }}
.bc-caps .bc-cap {{ animation: bc-rise .55s ease both; }}
.bc-caps .bc-cap:nth-child(1) {{ animation-delay: .24s; }} .bc-caps .bc-cap:nth-child(2) {{ animation-delay: .32s; }}
.bc-caps .bc-cap:nth-child(3) {{ animation-delay: .4s; }}
.bc-hero .bc-exhibit {{ animation: bc-rise .6s .48s ease both; }}
.bc-hero .foot {{ animation: bc-fade .6s .8s ease both; }}
.st-key-signin {{ animation: bc-rise .6s .12s ease both; }}
/* the exhibit plays the product in a few seconds: claim underlined, then each link of the trail, then the verdict */
.bc-exhibit .ring {{ background: linear-gradient({S.CORAL}, {S.CORAL}) no-repeat left bottom / 0% 2px, rgba(241,125,131,.18);
    box-shadow: none; animation: bc-ul .7s .9s ease forwards; }}
@keyframes bc-ul {{ to {{ background-size: 100% 2px, 100% 100%; }} }}
.bc-exhibit .bc-trail .node, .bc-exhibit .bc-trail .link {{ animation: bc-pop .4s ease both; }}
.bc-exhibit .bc-trail > :nth-child(1) {{ animation-delay: 1.5s; }} .bc-exhibit .bc-trail > :nth-child(2) {{ animation-delay: 1.65s; }}
.bc-exhibit .bc-trail > :nth-child(3) {{ animation-delay: 1.8s; }} .bc-exhibit .bc-trail > :nth-child(4) {{ animation-delay: 1.95s; }}
.bc-exhibit .bc-trail > :nth-child(5) {{ animation-delay: 2.1s; }} .bc-exhibit .bc-trail > :nth-child(6) {{ animation-delay: 2.25s; }}
.bc-exhibit .bc-trail > :nth-child(7) {{ animation-delay: 2.4s; }}
.bc-exhibit .verdict {{ animation: bc-pop .45s 2.7s ease both; }}
/* buttons and fields */
.st-key-signin button {{ transition: transform .15s ease, box-shadow .15s ease, background .15s ease; }}
.st-key-signin button:hover:not(:disabled) {{ transform: translateY(-1px); box-shadow: 0 6px 16px rgba(38,58,50,.16); }}
.st-key-signin button:active:not(:disabled) {{ transform: translateY(0) scale(.985); box-shadow: none; }}
.st-key-signin [data-baseweb="input"], .st-key-signin [data-baseweb="select"] > div {{ transition: box-shadow .18s ease, border-color .18s ease; }}
.st-key-signin [data-baseweb="input"]:focus-within, .st-key-signin [data-baseweb="select"] > div:focus-within {{
    box-shadow: 0 0 0 3px rgba(86,201,193,.28); border-color: {S.TURQUOISE}; }}
/* Sign in / Sign up switch */
.st-key-auth_mode, .st-key-auth_mode [data-testid="stRadio"] {{ width: 100% !important; }}
.st-key-auth_mode [data-testid="stWidgetLabel"] {{ display: none; }}
.st-key-auth_mode [data-testid="stRadioGroup"] {{ display: flex; width: 100%; gap: 4px; background: {S.SAGE_LIGHT}; border-radius: 14px;
    padding: 4px; margin: 2px 0 12px; }}
.st-key-auth_mode [data-testid="stRadioGroup"] > div {{ flex: 1; }}
.st-key-auth_mode [data-testid="stRadioOption"] {{ width: 100%; justify-content: center; margin: 0; padding: 8px 10px; border-radius: 11px;
    cursor: pointer; transition: background .2s ease, box-shadow .2s ease; box-sizing: border-box; }}
.st-key-auth_mode [data-testid="stRadioOption"] > div {{ justify-content: center; width: 100%; }}
.st-key-auth_mode [data-testid="stRadioOption"] > div > div:first-child {{ display: none; }}
.st-key-auth_mode [data-testid="stRadioOption"] p {{ font-weight: 600; font-size: .92rem; text-align: center; color: {S.MUTED}; }}
.st-key-auth_mode [data-testid="stRadioOption"][data-selected="true"] {{ background: {S.WHITE}; box-shadow: 0 2px 8px rgba(16,28,22,.12); }}
.st-key-auth_mode [data-testid="stRadioOption"][data-selected="true"] p {{ color: {S.TEXT}; }}
/* Continue with Google */
.st-key-g_btn button {{ background: #fff !important; border: 1px solid {S.BORDER} !important; }}
.st-key-g_btn button p {{ color: {S.TEXT} !important; font-weight: 600; display: flex; align-items: center; gap: 10px; }}
.st-key-g_btn button p::before {{ content: ""; width: 18px; height: 18px; flex: none; background: no-repeat center / contain url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath fill='%23EA4335' d='M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z'/%3E%3Cpath fill='%234285F4' d='M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z'/%3E%3Cpath fill='%23FBBC05' d='M10.5 28.7c-.5-1.5-.8-3-.8-4.7s.3-3.2.8-4.7l-7.9-6.1C.9 16.4 0 20.1 0 24s.9 7.6 2.6 10.8l7.9-6.1z'/%3E%3Cpath fill='%2334A853' d='M24 48c6.3 0 11.6-2.1 15.5-5.7l-7.5-5.8c-2.1 1.4-4.8 2.3-8 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z'/%3E%3C/svg%3E"); }}
.bc-or {{ display: flex; align-items: center; gap: 10px; color: {S.MUTED}; font-size: .78rem; margin: 10px 0 8px; }}
.bc-or::before, .bc-or::after {{ content: ""; flex: 1; height: 1px; background: {S.BORDER}; }}
/* sign-up steps */
[class*="st-key-su-step"] {{ animation: bc-slide .35s ease both; }}
.bc-steps3 {{ display: flex; align-items: center; gap: 8px; font-size: .76rem; font-weight: 700; color: {S.MUTED}; letter-spacing: .04em; text-transform: uppercase; }}
.bc-steps3 .on {{ color: {S.TEXT}; }}
.bc-prog {{ height: 6px; background: {S.SAGE_LIGHT}; border-radius: 99px; overflow: hidden; margin: 8px 0 14px; }}
.bc-prog i {{ display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, {S.TURQUOISE}, {S.GREEN}); animation: bc-grow .6s ease both; }}
.bc-meter {{ display: flex; gap: 4px; margin: 2px 0 6px; }}
.bc-meter i {{ flex: 1; height: 5px; border-radius: 99px; background: {S.SAGE_LIGHT}; }}
.bc-meter i.on {{ animation: bc-fade .4s ease both; }}
.bc-checks {{ display: grid; gap: 3px; font-size: .8rem; color: {S.MUTED}; margin-bottom: 8px; }}
.bc-checks .ok {{ color: {S.GREEN}; }}
.bc-checks .ok b {{ display: inline-block; animation: bc-pop .3s ease both; }}
.bc-sum {{ background: {S.SAGE_LIGHT}; border-radius: 16px; padding: 12px 14px; display: grid; gap: 8px; margin-bottom: 10px; }}
.bc-sum div {{ display: flex; justify-content: space-between; gap: 12px; font-size: .9rem; }}
.bc-sum span {{ color: {S.MUTED}; }} .bc-sum b {{ color: {S.TEXT}; text-align: right; }}
.bc-done {{ text-align: center; padding: 10px 4px 4px; animation: bc-fade .4s ease both; }}
.bc-done svg {{ width: 76px; height: 76px; }}
.bc-done circle {{ fill: none; stroke: {S.GREEN}; stroke-width: 3; stroke-dasharray: 176; stroke-dashoffset: 176; animation: bc-draw .6s .1s ease forwards; }}
.bc-done path {{ fill: none; stroke: {S.GREEN}; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 40;
    stroke-dashoffset: 40; animation: bc-draw .4s .6s ease forwards; }}
.bc-done .t {{ font-family: {S.DISPLAY}; font-weight: 800; font-size: 1.5rem; margin: 10px 0 2px; color: {S.TEXT}; }}
.bc-done p {{ color: {S.MUTED}; font-size: .92rem; margin: 0 0 12px; line-height: 1.5; }}
@media (prefers-reduced-motion: reduce) {{ *, *::before, *::after {{ animation: none !important; transition: none !important; }}
    .bc-done circle, .bc-done path {{ stroke-dashoffset: 0 !important; }} }}
</style>
"""

ICON = ('<svg viewBox="0 0 34 34" aria-hidden="true"><rect x="1" y="1" width="32" height="32" rx="9" fill="#263A32"/>'
        '<path d="M12 12L23 10.5M12 12L22 22.5M12 12L11 23M22 22.5L11 23M23 10.5L22 22.5" stroke="#B9CDBD" stroke-width="1.1" '
        'stroke-opacity=".7"/><circle cx="12" cy="12" r="3" fill="#56C9C1"/><circle cx="23" cy="10.5" r="2.4" fill="#E79BD0"/>'
        '<circle cx="22" cy="22.5" r="3.2" fill="#B9CDBD"/><circle cx="11" cy="23" r="2.2" fill="#AD83EE"/></svg>')


def _google_button(label):
    """'Continue with Google' is always on the page. Without credentials it explains what is missing instead of failing."""
    if st.button(label, key="g_btn", width="stretch"):
        ss.pop("g_skip", None)
        if not config.google_signin_ready():
            st.warning("Google sign-in is not switched on for this deployment yet: it needs a Google OAuth client and the "
                       "[auth] settings in Streamlit secrets (setup steps in docs/google_signin.md). Password sign-in "
                       "works meanwhile.", icon=":material/info:")
        else:
            try:
                prov = "google" if st.secrets["auth"].get("google") else None
                st.login(prov)
            except Exception:  # noqa: BLE001 - e.g. Authlib missing or a malformed secret; say so plainly
                st.error("Google sign-in could not start. Check the [auth] settings (see docs/google_signin.md).",
                         icon=":material/error:")
    st.markdown('<div class="bc-or">or</div>', unsafe_allow_html=True)


def _google_identity():
    """(email, name, verified) of the person signed in to Google in this browser, or None."""
    if not config.google_signin_ready():
        return None
    try:
        if not st.user.is_logged_in:
            return None
        return (str(st.user.get("email") or "").strip(), str(st.user.get("name") or "").strip(), bool(st.user.get("email_verified", True)))
    except Exception:  # noqa: BLE001
        return None


def _google_logout():
    try:
        st.logout()
    except Exception:  # noqa: BLE001
        st.rerun()


def _google_return():
    """Handle a person who has just come back from Google. Returns True when this page was fully drawn here."""
    who = _google_identity()
    if not who or ss.get("g_skip") or ss.get("su_done") or ss.get("_farewell") is not None:
        return False
    email, name, verified = who
    if not email or not verified:
        st.error("Google did not give a verified e-mail address, so BrandCanon cannot sign you in with it.", icon=":material/error:")
        st.button("Use a different account", key="g_other", on_click=_google_logout)
        return True
    if auth.find_by_email(email):
        _enter(auth.sign_in_google(email))
    return False


def _google_new(who):
    """A Google account BrandCanon has not seen: finish creating a workspace for it."""
    email, name, _ = who
    first = name.split(" ")[0] if name else "there"
    st.markdown(f'<div class="bc-login-title">Welcome, {c.esc(first)}</div><div class="bc-login-sub">You are signed in with Google as '
                f'<b>{c.esc(email)}</b>. This e-mail has no BrandCanon account yet. Create a workspace and you become its Brand '
                f'Manager, or ask a Brand Manager to add this e-mail.</div>', unsafe_allow_html=True)
    brand = st.text_input("Brand or company name", placeholder="e.g. Acme Foods", key="g_brand")
    if st.button("Create workspace", type="primary", icon=":material/add_business:", width="stretch", key="g_create"):
        try:
            user = auth.create_workspace_google(brand, name or email.split("@")[0], email)
        except auth.AuthError as e:
            st.error(str(e), icon=":material/error:")
        else:
            ss["su_done"] = dict(user, _brand=brand.strip())
            st.rerun()
    st.button("Use a different account", key="g_other2", type="tertiary", on_click=_google_logout)


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
    ss["_set_cookie"] = True
    ss.pop("_no_restore", None)
    for k in ("login_fails", "login_lock_until", "cur_sub", "probe_rule", "probe_select", "_farewell", "su", "su_step", "su_done"):
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
    me_row = next((p for p in people if p["id"] == uid), {})
    if not auth.has_password(uid) and me_row.get("email"):
        st.info("This account signs in with Google. Use the Google button above.", icon=":material/passkey:")
        return
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


def _strength(pw):
    """Quick visual hint only (0-4); the real rules are in auth.check_strength."""
    n = 0
    if len(pw) >= auth.MIN_LENGTH:
        n += 1
    if len(pw) >= 12:
        n += 1
    if any(ch.isdigit() for ch in pw) and any(ch.isalpha() for ch in pw):
        n += 1
    if (any(ch.islower() for ch in pw) and any(ch.isupper() for ch in pw)) or any(not ch.isalnum() for ch in pw):
        n += 1
    return n


def _meter(pw, pw2):
    n = _strength(pw) if pw else 0
    label = ["", "Weak", "Fair", "Good", "Strong"][n]
    colour = ["", S.CORAL, S.YELLOW, S.TURQUOISE, S.GREEN][n]
    bars = "".join(f'<i class="{"on" if i < n else ""}" style="{f"background:{colour}" if i < n else ""}"></i>' for i in range(4))
    rules = [(len(pw) >= auth.MIN_LENGTH, f"At least {auth.MIN_LENGTH} characters"),
             (bool(pw) and pw.strip() == pw, "No space at the start or end")]
    if pw2:
        rules.append((pw == pw2, "Both passwords match"))
    items = "".join(f'<div class="{"ok" if ok else ""}"><b>{"✓" if ok else "○"}</b> {c.esc(t)}</div>' for ok, t in rules)
    st.markdown(f'<div class="bc-meter">{bars}</div><div style="font-size:.78rem;color:{colour or S.MUTED};font-weight:700;'
                f'min-height:1.1em">{label}</div><div class="bc-checks">{items}</div>', unsafe_allow_html=True)


def _progress(step):
    names = ["Account", "Workspace", "Ready"]
    steps = "".join(f'<span class="{"on" if i + 1 <= step else ""}">{i + 1} · {n}</span>' for i, n in enumerate(names))
    st.markdown(f'<div class="bc-steps3">{steps}</div><div class="bc-prog"><i style="width:{step / 3 * 100:.0f}%;'
                f'--from:{(step - 1) / 3 * 100:.0f}%"></i></div>', unsafe_allow_html=True)


def _su_go(step, keep=None):
    """Move between steps; `keep` = (widget key, field) saves what was typed so Back never loses it."""
    if keep and keep[0] in ss:
        ss.setdefault("su", {})[keep[1]] = (ss[keep[0]] or "").strip()
    ss.su_step = step


def _create_tab():
    """Three-step sign-up: account → workspace → review. The person becomes the Brand Manager of the new workspace."""
    step = ss.get("su_step", 1)
    su = ss.setdefault("su", {"name": "", "pw": "", "brand": ""})
    _progress(step)
    with st.container(key=f"su-step{step}"):
        if step == 1:
            name = st.text_input("Your name", value=su["name"], placeholder="e.g. Asha Rao", key="su_name_in")
            pw = st.text_input("Password", type="password", value=su["pw"], key="su_pw_in", help=f"At least {auth.MIN_LENGTH} characters.")
            pw2 = st.text_input("Repeat the password", type="password", value=su["pw"], key="su_pw2_in")
            _meter(pw, pw2)
            if st.button("Continue", type="primary", icon=":material/arrow_forward:", icon_position="right", width="stretch", key="su_next1"):
                try:
                    if not name.strip():
                        raise auth.AuthError("Enter your name.")
                    if pw != pw2:
                        raise auth.AuthError("The two passwords do not match.")
                    auth.check_strength(pw)
                    su.update(name=name.strip(), pw=pw)
                    _su_go(2)
                    st.rerun()
                except auth.AuthError as e:
                    st.error(str(e), icon=":material/error:")
        elif step == 2:
            brand = st.text_input("Brand or company name", value=su["brand"], placeholder="e.g. Acme Foods", key="su_brand_in")
            if brand.strip():
                if auth.workspace_name_taken(brand):
                    st.markdown(f'<div class="bc-checks"><div style="color:{S.CORAL}"><b>✕</b> A workspace with this name already exists. '
                                'Ask its Brand Manager to add you, or pick another name.</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="bc-checks"><div class="ok"><b>✓</b> This name is available</div></div>', unsafe_allow_html=True)
            st.markdown('<div class="bc-note" style="margin-bottom:10px">You will be the <b>Brand Manager</b> of this workspace. Add reviewers and creators later '
                        'from Settings → Profile &amp; people.</div>', unsafe_allow_html=True)
            c1, c2 = st.columns([1, 1.6])
            c1.button("Back", icon=":material/arrow_back:", width="stretch", key="su_back2", on_click=_su_go, args=(1, ("su_brand_in", "brand")))
            if c2.button("Continue", type="primary", icon=":material/arrow_forward:", icon_position="right", width="stretch", key="su_next2"):
                if not brand.strip():
                    st.error("Enter the brand or company name.", icon=":material/error:")
                elif auth.workspace_name_taken(brand):
                    st.error("A workspace with this name already exists. Pick another name.", icon=":material/error:")
                else:
                    su["brand"] = brand.strip()
                    _su_go(3)
                    st.rerun()
        else:
            st.markdown(f'<div class="bc-sum"><div><span>Brand workspace</span><b>{c.esc(su["brand"])}</b></div>'
                        f'<div><span>Your name</span><b>{c.esc(su["name"])}</b></div><div><span>Your role</span><b>Brand Manager</b></div>'
                        f'<div><span>Password</span><b>{"•" * min(len(su["pw"]), 12)}</b></div></div>', unsafe_allow_html=True)
            c1, c2 = st.columns([1, 1.6])
            c1.button("Back", icon=":material/arrow_back:", width="stretch", key="su_back3", on_click=_su_go, args=(2,))
            if c2.button("Create workspace", type="primary", icon=":material/add_business:", width="stretch", key="su_create"):
                try:
                    user = auth.create_workspace(su["brand"], su["name"], su["pw"], su["pw"])
                except auth.AuthError as e:
                    st.error(str(e), icon=":material/error:")
                else:
                    ss["su_done"] = dict(user, _brand=su["brand"])
                    ss.pop("su", None)
                    ss.pop("su_step", None)
                    st.rerun()
    st.markdown('<div class="bc-fine">Your password is stored only as a salted hash. You can add more people after you sign in.</div>',
                unsafe_allow_html=True)


CHECK = ('<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="28"/><path d="M20 33l8 8 16-17"/></svg>')


def _enter_and_go(user, land=None):
    if land:
        ss["_land"] = land
    _enter(user)


def _done_card():
    user = ss["su_done"]
    st.markdown(f'<div class="bc-done">{CHECK}<div class="t">Workspace created</div><p><b>{c.esc(user.get("_brand") or "Your workspace")}</b> '
                f'is ready, {c.esc(user["name"].split()[0])}. You are its Brand Manager.</p></div>', unsafe_allow_html=True)
    if st.button("Upload brand documents", type="primary", icon=":material/upload_file:", width="stretch", key="done_docs"):
        _enter_and_go(user, "constitution")
    if st.button("Open my workspace", icon=":material/dashboard:", width="stretch", key="done_open"):
        _enter_and_go(user)
    if st.button("Explore the NovaTech demo first", type="tertiary", icon=":material/play_circle:", width="stretch", key="done_demo",
                 help="Your workspace is saved. Sign in to it any time."):
        demo_ws = next((w for w in q.list_workspaces() if w["is_demo"]), None)
        ss.pop("su_done", None)
        ss["g_skip"] = True   # stay on the sign-in page even if a Google session exists
        ss["auth_mode"] = "Sign in"
        if demo_ws:
            ss["login_ws"] = demo_ws["name"]
        st.rerun()


def _farewell_card():
    who = ss["_farewell"]
    st.markdown(f'<div class="bc-done">{CHECK}<div class="t">You&#8217;ve been signed out</div><p>See you soon{", " + c.esc(who) if who else ""}. '
                'Everything you saved is still in the workspace.</p></div>', unsafe_allow_html=True)
    if st.button("Sign in again", type="primary", icon=":material/login:", width="stretch", key="again"):
        ss.pop("_farewell", None)
        st.rerun()


def _demo_quick():
    """One click for anyone just looking: sign in as a demo person. The demo logins are shown so nothing is hidden."""
    demo_ws = next((w for w in q.list_workspaces() if w["is_demo"]), None)
    if not demo_ws:
        return
    people = {p["role"]: p for p in q.users(demo_ws["id"])}
    st.markdown('<div class="bc-fine" style="text-align:center;margin:12px 0 6px">or just look around</div>', unsafe_allow_html=True)

    def go(role):
        p = people.get(role)
        try:
            if not p:
                raise auth.AuthError(f"The demo workspace has no {role}.")
            _enter(auth.sign_in(p["id"], auth.DEMO_PASSWORD))
        except auth.AuthError:
            st.error("The demo password has been changed. Choose a demo person above and enter their password.", icon=":material/error:")

    if st.button(f"Try the demo as {people['Brand Manager']['name'] if 'Brand Manager' in people else 'Neha'} (Brand Manager)",
                 icon=":material/play_arrow:", width="stretch", key="demo_try"):
        go("Brand Manager")
    a, b = st.columns(2)
    if "Reviewer" in people and a.button(f"As {people['Reviewer']['name']} (Reviewer)", width="stretch", key="demo_rev"):
        go("Reviewer")
    if "Creator" in people and b.button(f"As {people['Creator']['name']} (Creator)", width="stretch", key="demo_cre"):
        go("Creator")
    st.markdown(f'<div class="bc-fine" style="text-align:center;margin-top:6px">Demo workspace <b>{esc(demo_ws["name"])}</b> · every '
                f'demo person signs in with the password <code>{esc(auth.DEMO_PASSWORD)}</code>. The three roles see different '
                'screens. It is a fictional brand.</div>', unsafe_allow_html=True)


def render():
    st.markdown(CSS, unsafe_allow_html=True)
    if ss.pop("_clear_cookie", False):
        c.clear_cookie(session_token.COOKIE)
    if not q.list_workspaces():
        with st.spinner("Preparing the NovaTech demonstration workspace…"):
            demo.reset(with_history=True)
    if _google_return():
        return
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
        if ss.get("_farewell") is not None:
            _farewell_card()
        elif ss.get("su_done"):
            _done_card()
        elif (gid := _google_identity()) and not ss.get("g_skip") and gid[0] and gid[2] and not auth.find_by_email(gid[0]):
            _google_new(gid)
        else:
            mode = st.radio("Mode", ["Sign in", "Sign up"], horizontal=True, key="auth_mode", label_visibility="collapsed")
            if mode == "Sign up":
                st.markdown('<div class="bc-login-title">Create your workspace</div>'
                            '<div class="bc-login-sub">Three quick steps. You become the Brand Manager.</div>', unsafe_allow_html=True)
                _google_button("Sign up with Google")
                _create_tab()
            else:
                st.markdown('<div class="bc-login-title">Sign in</div>'
                            '<div class="bc-login-sub">Choose your brand workspace and your name, then enter your password.</div>',
                            unsafe_allow_html=True)
                _google_button("Continue with Google")
                _sign_in_tab()
                _demo_quick()
            st.markdown('<div class="bc-fine">Passwords are stored as salted PBKDF2 hashes in the local database. This is '
                        'prototype sign-in: there is no single sign-on, multi-factor authentication or password recovery.</div>',
                        unsafe_allow_html=True)
