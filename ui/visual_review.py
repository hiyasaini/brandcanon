"""Visual review: a whole campaign's images in one place — deterministic checks, plus Gemini Vision when it is live."""
import csv
import io

import pandas as pd
import streamlit as st

import config
from modules import queries as q, rule_probe, visual_ai, visual_audit
from services import gemini_service as gs
from services.file_service import FileRejected, validate_upload
from ui import components as c, styles as S

ss = st.session_state
MAX_IMAGES = 8


def _palette(ws):
    palette, min_c = {}, 4.5
    for r in q.list_rules(ws, ("Approved",)):
        palette.update(r["constraints"].get("palette") or {})
        min_c = r["constraints"].get("min_contrast", min_c)
    return palette, min_c


def _run(ws, files, alts, channel, product, logo, fg, bg):
    palette, min_c = _palette(ws)
    items = []
    for f, alt in zip(files, alts):
        data = f.getvalue()
        it = {"name": f.name, "data": data, "alt": alt, "det": None, "ai": None, "ai_error": None, "error": None}
        try:
            validate_upload(f.name, data, config.ALLOWED_IMAGE_EXTENSIONS)
            it["det"] = visual_audit.audit(data, channel, alt, palette, min_c, fg, bg, logo.getvalue() if logo else None)
            it["min_c"] = min_c
        except (FileRejected, ValueError) as e:
            it["error"] = str(e)
            items.append(it)
            continue
        if gs.enabled():
            try:
                it["ai"] = visual_ai.review(ws, data, channel, product, alt)
            except (gs.GeminiError, ValueError) as e:
                it["ai_error"] = e.message if isinstance(e, gs.GeminiError) else str(e)
        items.append(it)
    return items


def _form(ws, user):
    with c.card(key="panel-vrform"):
        c.card_title("Campaign images", f"up to {MAX_IMAGES} at once · reviewed together")
        products = q.products(ws) or ["General"]
        a, b, d = st.columns([1.4, 1, 1])
        a.text_input("Campaign name", key="vr_name", placeholder="e.g. NovaTech X1 launch")
        channel = b.selectbox("Channel", [x for x in config.CHANNELS if x != "All content"], index=1, key="vr_channel")
        product = d.selectbox("Product", products, index=products.index(rule_probe.main_product(ws)) if rule_probe.main_product(ws) in products else 0,
                              key="vr_product")
        files = st.file_uploader("Images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="vr_files")
        if files and len(files) > MAX_IMAGES:
            st.warning(f"Only the first {MAX_IMAGES} images are reviewed.", icon=":material/warning:")
            files = files[:MAX_IMAGES]
        alts = []
        if files:
            st.markdown("<span class='bc-muted'>Alternative text for each image (empty alt text is reported):</span>", unsafe_allow_html=True)
            for i, f in enumerate(files):
                alts.append(st.text_input(f.name, key=f"vr_alt_{i}_{f.name}", label_visibility="visible", placeholder="Describe the image for screen readers"))
        e1, e2, e3 = st.columns([1.4, 1, 1])
        logo = e1.file_uploader("Approved logo (optional)", type=["png", "jpg", "jpeg", "webp"], key="vr_logo")
        fg = e2.color_picker("Text colour", "#FFFFFF", key="vr_fg", help="Used for the contrast measurement.")
        bg = e3.color_picker("Background behind the text", "#242522", key="vr_bg")
        if gs.enabled():
            st.caption("Live Gemini is on: each image is also sent to Google's Gemini API for logo, layout, in-image text and "
                       "accessibility observations. Nothing is stored by BrandCanon.")
        else:
            st.caption("Live Gemini is off, so only the deterministic checks run: size, palette, contrast, alt text and logo match. "
                       "Turn on Gemini to add observations about layout, in-image text and accessibility.")
        if st.button("Review the campaign", type="primary", icon=":material/image_search:", disabled=not files, key="vr_go", width="stretch"):
            with st.spinner(f"Reviewing {len(files)} image(s)…"):
                ss["vr_res"] = {"name": ss.get("vr_name") or "Untitled campaign", "channel": channel, "product": product,
                                "items": _run(ws, files, alts, channel, product, logo, fg, bg), "engine_on": gs.enabled()}
                ss["vr_pick"] = 0
            st.rerun()


def _issue_rows(it):
    """Everything found for one image as flat rows: (severity, source, category, message, suggestion, where)."""
    rows = []
    for sev, msg in (it["det"] or {}).get("findings", []):
        rows.append((sev, "Deterministic check", "Measured", msg, "", ""))
    for n, x in enumerate((it["ai"] or {}).get("issues", []), 1):
        rows.append((x["severity"], "Gemini Vision", x["category"], x["message"], x["suggestion"], f"#{n}" if x["box"] else ""))
    ta = (it["ai"] or {}).get("text_audit")
    if ta:
        for f in ta["findings"]:
            if f["classification"] != "Verified":
                rows.append((f["severity"], "Claim checker (text read from the image)", f["classification"], f["message"],
                             f["suggestion"] or "", ""))
    return rows


def _csv(res):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["campaign", "image", "severity", "found by", "type", "issue", "suggestion", "marker"])
    for it in res["items"]:
        if it["error"]:
            w.writerow([res["name"], it["name"], "", "", "", f"Not reviewed: {it['error']}", "", ""])
        for r in _issue_rows(it):
            w.writerow([res["name"], it["name"], *r])
    return out.getvalue()


def _results(ws, res):
    items = res["items"]
    rows = []
    for it in items:
        if it["error"]:
            rows.append({"Image": it["name"], "Size": "—", "High": "—", "Medium": "—", "Low": "—", "Gemini": "not reviewed"})
            continue
        cnt = visual_ai.summarise(it["det"], it["ai"])
        rows.append({"Image": it["name"], "Size": f"{it['det']['size'][0]}×{it['det']['size'][1]}", "High": cnt["high"], "Medium": cnt["medium"],
                     "Low": cnt["low"], "Gemini": ("failed" if it["ai_error"] else ("reviewed" if it["ai"] else "off"))})
    c.card_title(f"{res['name']} · campaign summary", f"{len(items)} image(s) · {res['channel']}")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    failed = [it for it in items if it["ai_error"]]
    if failed:
        st.error(f"Gemini Vision did not review {len(failed)} image(s): " + failed[0]["ai_error"] + " Their deterministic checks are shown; "
                 "no AI result is claimed for them.", icon=":material/cloud_off:")
    names = [f"{i + 1}. {it['name']}" for i, it in enumerate(items)]
    pick = st.radio("Image", names, index=min(ss.get("vr_pick", 0), len(names) - 1), horizontal=True, key="vr_pick_r", label_visibility="collapsed")
    it = items[names.index(pick)]
    if it["error"]:
        st.error(it["error"], icon=":material/error:")
        return
    ai = it["ai"]
    left, right = st.columns([1, 1.25])
    with left, c.card(key="card-vrimg"):
        shown = visual_ai.annotate(it["data"], ai["issues"]) if ai and any(x["box"] for x in ai["issues"]) else it["data"]
        st.image(shown, width="stretch")
        d = it["det"]
        st.markdown(f"**{d['size'][0]}×{d['size'][1]} px**" + (f" · text contrast **{d['contrast']}:1** (brand minimum {it['min_c']}:1)" if d["contrast"] else "")
                    + (f" · logo match **{d['logo_score']:.2f}**" if d["logo_score"] is not None else ""))
        if ai and ai["text_in_image"]:
            st.markdown(f"<span class='bc-muted'>Text read from the image by Gemini:</span><div class='bc-quote'>{c.esc(ai['text_in_image'])}</div>",
                        unsafe_allow_html=True)
    with right, c.card(key="card-vrissues"):
        c.card_title("Issues", "each one shows what found it")
        rows = _issue_rows(it)
        if not rows:
            st.success("No issues found by the checks that ran.", icon=":material/task_alt:")
        for sev, src, typ, msg, sug, where in rows:
            st.markdown(c.badge(sev.capitalize(), c.STATUS_TONE.get(sev, "neutral")) + c.badge(typ, "neutral") + (f" <b>{where}</b>" if where else "")
                        + f"<div style='margin:4px 0 2px'>{c.esc(msg)}</div><span class='bc-muted' style='font-size:.78rem'>{c.esc(src)}</span>"
                        + (f"<div class='bc-muted' style='font-size:.82rem'>Suggestion: {c.esc(sug)}</div>" if sug else ""), unsafe_allow_html=True)
        if ai:
            for n, x in enumerate(ai["issues"], 1):
                if x["rule_code"]:
                    st.caption(f"#{n} relies on {x['source']}")
                elif x["box"]:
                    st.caption(f"#{n}: {x['source']}")
            st.markdown(c.engine_tag(ai["engine"]), unsafe_allow_html=True)
        elif res["engine_on"] is False:
            st.caption("Deterministic checks only (live Gemini is off).")
    st.download_button("Download all issues (CSV)", _csv(res), "campaign_visual_review.csv", "text/csv", icon=":material/download:", key="vr_csv")


def render(ws, user):
    st.markdown("<span class='bc-muted'>Review every image of a campaign in one place. Deterministic checks always run (size, palette, "
                "contrast, alt text, logo). With live Gemini, each image is also examined for logo use, layout, accessibility and "
                "in-image text; issues are marked on the picture and cite a brand rule only when one applies. Results are shown here "
                "and not stored.</span>", unsafe_allow_html=True)
    _form(ws, user)
    res = ss.get("vr_res")
    if res:
        _results(ws, res)
