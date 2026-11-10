"""Content Intelligence (Content Auditor) — examine content before it reaches your audience.

Split screen: a large content editor on the left (with the audited text marked up), clickable finding cards on the right.
Selecting a finding highlights its phrase and opens its explanation, the approved rule, the source document and passage,
and a suggested correction. Contradicted, Unsupported and Unverifiable are kept distinct; nothing is called false without
conflicting evidence.
"""
import streamlit as st

import config
from modules import approval_workflow as aw, content_audit, demo, queries as q, report_generator, rule_probe, visual_audit
from modules.document_parser import ParseError, parse
from services import gemini_service as gs
from services.file_service import FileRejected, validate_upload
from ui import components as c

ss = st.session_state
TABS = ["Audit", "Drafts and submissions"]
SEV_RANK = {"high": 0, "medium": 1, "low": 2, "info": 3}
EDITABLE = ("Draft", "Changes requested", "In review")
TYPE_COLOR = {"Tone mismatch": "#F0CF72", "Terminology violation": "#56C9C1", "Messaging inconsistency": "#AD83EE",
              "Contradicted claim": "#F17D83", "Unsupported claim": "#F0CF72", "Unverifiable claim": "#E79BD0",
              "Accessibility": "#718A7B"}


def ftype(f):
    """The reader-facing finding type, derived from the stored category and classification."""
    if f["classification"] in ("Contradicted", "Unsupported", "Unverifiable") and f["category"] in ("Claims", "Product facts", "Campaign"):
        return f"{f['classification']} claim"
    return {"Tone": "Tone mismatch", "Terminology": "Terminology violation", "Messaging": "Messaging inconsistency",
            "Accessibility": "Accessibility"}.get(f["category"], f["category"])


def _load_file():
    up = ss.get("ca_file")
    if not up:
        return
    try:
        ext = validate_upload(up.name, up.getvalue())
        pages = parse(ext, up.getvalue())
        text = "\n\n".join(t.strip() for _, t in pages if t and t.strip())
        if not text:
            raise ParseError("No text could be extracted from this file (it may be a scanned image).")
        ss.ca_text = text[:8000]
        ss.ca_title = ss.get("ca_title") or up.name.rsplit(".", 1)[0]
        ss["_ca_loaded"] = f"Loaded the text of {up.name} into the editor."
    except (FileRejected, ParseError, ValueError) as e:
        ss["_ca_loaded_err"] = str(e)


# ------------------------------------------------------------------ new audit (left, empty state)
def _new_form(ws, user):
    with c.card(key="card-editor"):
        c.card_title("Content editor", "paste text or load a document")
        products = q.products(ws) or ["General"]
        main = rule_probe.main_product(ws)
        if ss.get("ca_prefill"):
            ss.ca_text, ss.ca_title = ss.pop("ca_prefill")
        title = st.text_input("Title", key="ca_title", placeholder="e.g. NovaTech X1 launch post")
        a, b = st.columns(2)
        ctype = a.selectbox("Content type", config.CONTENT_TYPES, key="ca_type")
        channel = b.selectbox("Channel", [x for x in config.CHANNELS if x != "All content"], key="ca_channel")
        a, b = st.columns(2)
        product = a.selectbox("Product", products, index=products.index(main) if main in products else 0, key="ca_product")
        campaign = b.text_input("Campaign (optional)", key="ca_campaign", placeholder="e.g. Back to campus 2026")
        text = st.text_area("Content", key="ca_text", height=260,
                            placeholder="Paste the caption, email, advertisement, product description or web copy…")
        st.file_uploader("Or load the text from a document (PDF or DOCX)", type=["pdf", "docx"], key="ca_file",
                         on_change=_load_file, help="The text is extracted into the editor; you can edit it before auditing.")
        if ss.get("_ca_loaded"):
            st.caption(ss.pop("_ca_loaded"))
        if ss.get("_ca_loaded_err"):
            c.error(ss.pop("_ca_loaded_err"))
        use_ai = st.toggle("Add a live Gemini review of tone, messaging and claims", value=gs.enabled(), disabled=not gs.enabled(),
                           key="ca_ai", help="Deterministic checks always run. Gemini adds contextual findings; every quote "
                                             "must exist in your text.")
        if gs.enabled() and use_ai:
            st.caption("This text will be sent to Google's Gemini API after emails and phone numbers are removed.")
        x, y = st.columns([1.2, 1])
        go_ = x.button("Submit for audit", type="primary", icon=":material/plagiarism:", width="stretch", disabled=not text.strip())
        if ss.get("ws_name") == demo.DEMO_NAME and y.button("Use the NovaTech example", width="stretch"):
            ss.ca_prefill = (demo.DEMO_POST, "NovaTech X1 battery post")
            st.rerun()
    if go_:
        res = c.run_action(aw.create_draft, ws, user["id"], title or "Untitled", text, ctype, channel, product, campaign,
                           use_ai=use_ai)
        if res:
            ss.cur_sub, ss.ca_focus = res[0], None
            st.rerun()


# ------------------------------------------------------------------ editor (left, open submission)
def _editor(ws, user, sub, revs, rev, rep, fs):
    editable = sub["status"] in EDITABLE and (user["id"] == sub["author_id"] or user["role"] != "Creator")
    if len(revs) > 1:
        first = q.latest_report(revs[0]["id"])
        n0 = sum(1 for f in q.findings(first["id"]) if f["classification"] != "Verified") if first else None
        n1 = sum(1 for f in fs if f["classification"] != "Verified" and f["disposition"] != "dismissed")
        if n0 is not None:
            with c.card():
                st.markdown(c.before_after(revs[0]["text"], rev["text"], n0, n1), unsafe_allow_html=True)
    with c.card(key="card-editor"):
        st.markdown(f"<div class='bc-mono'>#{sub['id']} · {c.esc(sub['content_type'])} · {c.esc(sub['channel'])} · "
                    f"{c.esc(sub['product'] or '—')}{' · ' + c.esc(sub['campaign']) if sub.get('campaign') else ''} · revision "
                    f"{rev['revision_no']} · {c.esc(sub['author_name'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='bc-specimen-rule'>{c.esc(sub['title'])}</div>{c.badge(sub['status'])}", unsafe_allow_html=True)
        focus = ss.get("ca_focus")
        st.markdown(c.highlighted(rev["text"], fs, focus if isinstance(focus, int) and focus < len(fs) else None),
                    unsafe_allow_html=True)
        if focus is not None:
            if st.button("Show all marks", key="unfocus", type="tertiary", icon=":material/visibility:"):
                ss.ca_focus = None
                st.rerun()
        st.write("")
        with st.expander("Edit manually", expanded=bool(ss.get("ca_manual")), icon=":material/edit:"):
            new = st.text_area("Edit and resubmit", rev["text"], key=f"edit{rev['id']}", height=150, disabled=not editable)
            note = st.text_input("What changed? (optional)", key=f"note{rev['id']}", disabled=not editable)
        a, b = st.columns(2)
        changed = new.strip() != rev["text"].strip()
        if a.button("Re-run audit", key="rerun", type="primary" if changed else "secondary", icon=":material/refresh:",
                    width="stretch", disabled=not editable):
            if c.run_action(aw.add_revision, ws, user["id"], sub["id"], new, note or ("Edited and re-audited" if changed else "Re-run audit"),
                            success="New revision audited" if changed else "Audit re-run"):
                ss.ca_focus, ss.ca_manual = None, False
                st.rerun()
        if sub["status"] in ("Draft", "Changes requested"):
            if b.button("Submit for approval", key="submit", icon=":material/send:", width="stretch",
                        disabled=user["id"] != sub["author_id"] and user["role"] == "Creator"):
                if c.run_action(aw.submit, ws, user["id"], sub["id"], success="Submitted for review"):
                    st.rerun()
        else:
            b.button(f"{sub['status']}", key="status_btn", disabled=True, width="stretch")
        st.download_button("Save report", report_generator.audit_markdown(sub["id"]), f"brandcanon_audit_{sub['id']}.md",
                           icon=":material/download:", width="stretch", help="Downloads the audit report as Markdown.")
        _rewrite(ws, user, sub, rev, fs, editable)
    if len(revs) > 1:
        with c.card():
            st.markdown(f"#### Revision comparison · {len(revs)} revisions")
            labels = [f"Revision {r['revision_no']}" for r in revs]
            a, b = st.columns(2)
            i = a.selectbox("From", labels, index=0, key=f"cmp_a{sub['id']}_{len(revs)}")
            j = b.selectbox("To", labels, index=len(labels) - 1, key=f"cmp_b{sub['id']}_{len(revs)}")
            st.markdown(c.diff(revs[labels.index(i)]["text"], revs[labels.index(j)]["text"]), unsafe_allow_html=True)
    with c.card():
        st.markdown("#### Comments")
        for cm in q.comments(sub["id"]):
            st.markdown(f"<span class='bc-mono'>{c.esc(cm['user_name'])} · {cm['user_role']} · {cm['created_at'][:16].replace('T', ' ')}</span>"
                        f"<br><span style='font-size:.9rem'>{c.esc(cm['text'])}</span>", unsafe_allow_html=True)
        msg = st.text_input("Add a comment for the reviewer", key=f"cm{sub['id']}")
        if st.button("Post comment", disabled=not msg.strip(), key="post_cm"):
            if c.run_action(aw.comment, sub["id"], user["id"], msg, rev["revision_no"]):
                st.rerun()
    _visual(ws, sub)


def _rewrite(ws, user, sub, rev, fs, editable):
    """Optional Gemini full rewrite — a proposal; a person decides whether to save it as a revision."""
    issues = [f for f in fs if f["classification"] != "Verified" and f["disposition"] != "dismissed"]
    if not issues or not editable:
        return
    key = f"rw{rev['id']}"
    if not gs.enabled():
        st.caption("Full rewrites need live Gemini (AI_PROVIDER=gemini). Per-finding corrections on the right are deterministic.")
        return
    if st.button("Suggest a full rewrite with Gemini", icon=":material/auto_awesome:", width="stretch", key="rw_btn"):
        with st.spinner("Asking Gemini for a corrected version…"):
            try:
                ss[key] = content_audit.ai_rewrite(ws, rev["text"], fs, sub["product"], sub["channel"])
            except (gs.GeminiError, ValueError) as e:
                ss[key] = {"error": str(e)}
    prop = ss.get(key)
    if not prop:
        return
    if prop.get("error"):
        st.error(f"No rewrite: {prop['error']}", icon=":material/cloud_off:")
        return
    st.markdown("Proposed by " + c.engine_tag(prop["engine"]), unsafe_allow_html=True)
    st.markdown(c.diff(rev["text"], prop["text"]), unsafe_allow_html=True)
    a, b = st.columns(2)
    if a.button("Use this rewrite", type="primary", key=f"use{key}", width="stretch"):
        if c.run_action(aw.add_revision, ws, user["id"], sub["id"], prop["text"], f"Gemini rewrite accepted by {user['name']}",
                        success="Rewrite saved as a new revision and re-audited"):
            ss.pop(key, None)
            st.rerun()
    if b.button("Discard", key=f"dis{key}", width="stretch"):
        ss.pop(key, None)
        st.rerun()


# ------------------------------------------------------------------ findings (right)
def _finding_card(ws, user, sub, i, f, fs, editable):
    open_ = f["disposition"] == "open"
    sel = ss.get("ca_focus") == i
    typ = ftype(f)
    col = TYPE_COLOR.get(typ, "#B9CDBD")
    with c.card(key=f"card-f{f['id']}"):
        st.markdown(f'<div class="bc-finding {f["severity"]}"><div class="tag" style="display:flex;justify-content:space-between">'
                    f'<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{col};'
                    f'margin-right:6px"></span>#{i + 1} · {c.esc(typ)}</span><span>{c.esc(f["severity"])} severity</span></div>'
                    f'<div class="phrase">“{c.esc(f["quote"] or "whole text")}”</div></div>', unsafe_allow_html=True)
        st.markdown(c.badge(f["classification"]) + c.badge("root cause: " + f["root_cause"], "neutral")
                    + (c.badge(f["disposition"]) if not open_ else ""), unsafe_allow_html=True)
        if not sel:
            st.markdown(f"<div class='bc-muted' style='margin-top:4px'>{c.esc(f['message'][:120])}"
                        f"{'…' if len(f['message']) > 120 else ''}</div>", unsafe_allow_html=True)
            if st.button("Examine finding", key=f"fx{f['id']}", type="tertiary", icon=":material/my_location:",
                         help="Highlights the phrase in the text and opens the evidence."):
                ss.ca_focus = i
                st.rerun()
            return
        st.markdown(f"<div style='font-size:.92rem;margin:8px 0'>{c.esc(f['message'])}</div>", unsafe_allow_html=True)
        prec = f.get("precedents") or []
        st.markdown(c.finding_trail(f, prec[0] if prec else None), unsafe_allow_html=True)
        if f.get("rule_id"):
            r = q.get_rule(f["rule_id"])
            if r:
                st.markdown(f"<div class='bc-muted' style='margin-top:6px'>Related approved rule</div>"
                            f"<div style='font-size:.88rem'>{c.code(r['code'])} {c.esc(r['text'])}</div>", unsafe_allow_html=True)
        if f["evidence_text"]:
            st.markdown("<div class='bc-muted' style='margin-top:6px'>Supporting passage</div>", unsafe_allow_html=True)
            st.markdown(c.quote(f["evidence_text"], f["evidence_source"]), unsafe_allow_html=True)
            page = q.source_page(f["passage_id"]) if f.get("passage_id") else None
            if page:
                with st.expander(f"View source page · {page['doc_title']} {page['location']}", icon=":material/description:"):
                    st.markdown(c.source_page(page, f["passage_id"]), unsafe_allow_html=True)
        if prec:
            p = prec[0]
            st.markdown(f"<div class='bc-precedent'><b>An earlier review addressed a similar claim.</b> "
                        f"{c.esc(p['decision'])} by {c.esc(p['reviewer_name'])} on {p['created_at'][:10]}"
                        + (" · <i>based on an older source version</i>" if p.get("stale") else "") + "</div>", unsafe_allow_html=True)
            if st.button("View previous decision", key=f"pv{f['id']}", type="tertiary", icon=":material/history_edu:"):
                c.go("decisions", dm_decision=p["id"], dm_tab="Decision history")
        st.markdown('<div class="bc-prov">Produced by ' + c.engine_tag(f["engine"]) + f" · {c.esc(f['confidence'])} confidence</div>",
                    unsafe_allow_html=True)
        if f["disposition_reason"]:
            st.caption(f"{f['disposition']}: {f['disposition_reason']}")
        actionable = open_ and editable and f["classification"] != "Verified"
        rep = None
        if actionable and f.get("span_end"):
            st.markdown("<div class='bc-correction'><div class='k'>Suggested correction</div></div>", unsafe_allow_html=True)
            rep = st.text_input("Suggested correction (edit it before accepting)", f["suggestion"], key=f"rep{f['id']}",
                                label_visibility="collapsed",
                                help="Corrections keep the rest of your text and only replace the marked phrase.")
        if not actionable:
            if st.button("Close", key=f"fc{f['id']}", type="tertiary", icon=":material/close:"):
                ss.ca_focus = None
                st.rerun()
            return
        with st.container(horizontal=True, gap="small"):
            if rep is not None and st.button("Accept suggestion", key=f"acc{f['id']}", type="primary", icon=":material/check:",
                                             disabled=not f["suggestion"] and not rep):
                if c.run_action(aw.apply_and_revise, ws, user["id"], sub["id"], fs, {i: rep},
                                f"Accepted correction #{i + 1}" if rep == f["suggestion"] else f"Edited correction #{i + 1}",
                                success="Correction applied as a new revision and re-audited"):
                    ss.ca_focus = None
                    st.rerun()
            if st.button("Edit manually", key=f"em{f['id']}", icon=":material/edit:"):
                ss.ca_manual = True
                st.rerun()
            with st.popover("Dismiss finding", icon=":material/do_not_disturb_on:"):
                why = st.text_input("Why is this not an issue here?", key=f"dw{f['id']}")
                if st.button("Dismiss finding", key=f"db{f['id']}", disabled=not why.strip(), type="primary"):
                    if c.run_action(aw.dismiss_finding, ws, user["id"], f["id"], why, success="Finding dismissed"):
                        ss.ca_focus = None
                        st.rerun()


def _findings(ws, user, sub, rev, rep, fs):
    editable = sub["status"] in EDITABLE and (user["id"] == sub["author_id"] or user["role"] != "Creator")
    order = sorted(range(len(fs)), key=lambda i: (SEV_RANK[fs[i]["severity"]], i))
    major = [i for i in order if fs[i]["severity"] in ("high", "medium") and fs[i]["classification"] != "Verified"]
    minor = [i for i in order if fs[i]["severity"] == "low" and fs[i]["classification"] != "Verified"]
    verified = [i for i in order if fs[i]["classification"] == "Verified"]
    m = st.columns(3)
    with m[0]:
        c.metric("Review status", rep["overall_status"], f"revision {rev['revision_no']}",
                 "alert" if rep["n_high"] else ("warn" if major or minor else "ok"), icon="audit")
    with m[1]:
        c.metric("Critical and major", len(major), f"{rep['n_high']} high · {rep['n_medium']} medium", "alert" if rep["n_high"] else "",
                 icon="conflict")
    with m[2]:
        c.metric("Verified claims", len(verified), "match approved sources", "ok", icon="decision")
    types = {}
    for i in major + minor:
        if fs[i]["disposition"] != "dismissed":
            types[ftype(fs[i])] = types.get(ftype(fs[i]), 0) + 1
    if types:
        st.markdown(c.legend([(f"{k} · {n}", TYPE_COLOR.get(k, "#B9CDBD")) for k, n in types.items()]), unsafe_allow_html=True)
    st.markdown('<div class="bc-prov">Audit produced by ' + c.engine_tag(rep["engine"]) + "</div>", unsafe_allow_html=True)
    c.engine_alert(rep["engine"])
    st.caption("No single compliance score: each finding stands on its own evidence. Unsupported means no approved evidence; "
               "Unverifiable means the information cannot settle it; only Contradicted means evidence conflicts.")
    applicable = {i: fs[i]["suggestion"] for i in major + minor
                  if fs[i]["suggestion"] and fs[i].get("span_end") and fs[i]["disposition"] == "open"}
    if applicable and editable:
        if st.button(f"Accept all {len(applicable)} suggested corrections", type="primary", icon=":material/auto_fix_high:",
                     width="stretch", key="acc_all"):
            if c.run_action(aw.apply_and_revise, ws, user["id"], sub["id"], fs, applicable,
                            success="Corrections applied as a new revision and re-audited"):
                ss.ca_focus = None
                st.rerun()
    if not major and not minor:
        st.success("No issues found against validated rules and approved sources.", icon=":material/verified:")
    for i in major:
        _finding_card(ws, user, sub, i, fs[i], fs, editable)
    if minor:
        with st.expander(f"Minor suggestions · {len(minor)}"):
            for i in minor:
                _finding_card(ws, user, sub, i, fs[i], fs, editable)
    if verified:
        with st.expander(f"Verified claims · {len(verified)}"):
            for i in verified:
                f = fs[i]
                st.markdown(f"{c.badge('Verified')} **“{c.esc(f['quote'])}”** — {c.esc(f['message'])}", unsafe_allow_html=True)
                st.markdown(c.quote(f["evidence_text"], f["evidence_source"]), unsafe_allow_html=True)


def _current(ws, user):
    sid = ss.cur_sub
    sub = q.get_submission(sid)
    if not sub:
        ss.cur_sub = None
        st.rerun()
    revs = q.revisions(sid)
    rev = revs[-1]
    rep, fs = aw.report_with_context(ws, rev["id"], exclude_submission=sid)
    left, right = st.container(key="wrap-au").columns([1.05, 1])
    with left:
        _editor(ws, user, sub, revs, rev, rep, fs)
    with right:
        c.card_title("Audit findings", "select a finding to examine its evidence")
        if rep:
            _findings(ws, user, sub, rev, rep, fs)
        else:
            c.empty("No audit yet", "Re-run the audit to see findings.")


def _visual(ws, sub):
    with st.expander("Visual check (optional) — basic deterministic checks of a creative"):
        st.caption("Checks image size for the channel, colours against the brand palette, text contrast, alt text and — if you "
                   "upload the approved logo — logo presence. Results are shown here and not stored.")
        a, b = st.columns(2)
        img = a.file_uploader("Creative", type=["png", "jpg", "jpeg", "webp"], key="vis_img")
        logo = b.file_uploader("Approved logo (optional)", type=["png", "jpg", "jpeg", "webp"], key="vis_logo")
        alt = st.text_input("Alt text for this image", key="vis_alt")
        palette, min_c = {}, 4.5
        for r in q.list_rules(ws, ("Approved",)):
            palette.update(r["constraints"].get("palette") or {})
            min_c = r["constraints"].get("min_contrast", min_c)
        x, y = st.columns(2)
        fg = x.color_picker("Text colour in the creative", "#FFFFFF")
        bg = y.color_picker("Background behind the text", "#242522")
        if img:
            try:
                validate_upload(img.name, img.getvalue(), config.ALLOWED_IMAGE_EXTENSIONS)
                res = visual_audit.audit(img.getvalue(), sub["channel"], alt, palette, min_c, fg, bg, logo.getvalue() if logo else None)
            except (FileRejected, ValueError) as e:
                c.error(str(e))
                return
            p, r = st.columns([1, 1.3])
            p.image(img.getvalue(), width="stretch")
            with r:
                st.markdown(f"**{res['size'][0]}×{res['size'][1]} px** · contrast **{res['contrast']}:1** (brand minimum {min_c}:1)"
                            + (f" · logo match **{res['logo_score']:.2f}**" if res["logo_score"] is not None else ""))
                if not res["findings"]:
                    st.success("No visual issues found by these checks.")
                for sev, msg in res["findings"]:
                    st.markdown(c.badge(sev.capitalize(), c.STATUS_TONE[sev]) + " " + c.esc(msg), unsafe_allow_html=True)


def _list(ws, user):
    subs = q.list_submissions(ws, author_id=user["id"] if user["role"] == "Creator" else None)
    if not subs:
        c.empty("Nothing audited yet", "Submit content in the Audit tab. Drafts and submissions appear here.")
        return
    for s in subs:
        with c.card():
            a, b, cc = st.columns([3, 1.5, 1], vertical_alignment="center")
            a.markdown(f"**{c.esc(s['title'])}**<br><span class='bc-mono'>{c.esc(s['channel'])} · revision {s['latest_revision']} · "
                       f"{c.esc(s['author_name'])} · {s['updated_at'][:10]}</span>", unsafe_allow_html=True)
            b.markdown(c.badge(s["status"]), unsafe_allow_html=True)
            if cc.button("Open", key=f"open{s['id']}", width="stretch"):
                ss.cur_sub, ss.ca_focus, ss.aud_tab = s["id"], None, "Audit"   # nav key: applied before the tabs are drawn
                st.rerun()


def render():
    ws, user = c.ctx()
    c.flash()
    if "cur_sub" in ss and ss.get("cur_sub_ws") != ws:
        ss.cur_sub = None
    ss.cur_sub_ws = ws
    if c.take("aud_new"):
        ss.cur_sub, ss.ca_focus = None, None
        ss["aud_tab"] = "Audit"
    ss.setdefault("ca_manual", False)
    if (nav_sub := c.take("aud_sub")) is not None:
        ss.cur_sub, ss.ca_focus = nav_sub, None
        ss["aud_tab"] = "Audit"

    def new_audit():
        ss.cur_sub, ss.ca_focus = None, None
        ss["aud_tab"] = "Audit"
    c.page_head("Content Intelligence", "Examine content before it reaches your audience.",
                [("New audit", new_audit, "secondary", ":material/add:")] if ss.get("cur_sub") else [])
    t = c.tabs(TABS, "aud_tabs", "aud_tab")
    with t[0]:
        if ss.get("cur_sub"):
            _current(ws, user)
        else:
            left, right = st.container(key="wrap-aunew").columns([1.05, 1])
            with left:
                _new_form(ws, user)
            with right:
                c.card_title("Audit findings")
                c.empty("Findings appear here", "Each issue is shown with the phrase, its severity and classification, the rule "
                        "and source page it relies on, and a correction that keeps your message.")
    with t[1]:
        _list(ws, user)
