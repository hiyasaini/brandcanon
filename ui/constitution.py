"""Brand Constitution — your organisation's approved brand knowledge.

A document library of cards, knowledge categories, and — when a document is opened — a split workspace: the document
(information and its stored pages), the knowledge extracted from it, and the source details with approval controls.
Nothing extracted becomes policy until a Brand Manager approves it.
"""
from collections import Counter

import pandas as pd
import streamlit as st

import config
from modules import brand_constitution as bc, demo, document_ingestion as di, queries as q, rule_probe
from modules.document_parser import ParseError
from services import gemini_service as gs
from services.file_service import FileRejected
from ui import components as c
from ui import styles as S

ss = st.session_state
IS_BM = lambda u: u["role"] == "Brand Manager"  # noqa: E731
CATS = list(dict.fromkeys(config.DISPLAY_CATEGORY.values()))
STATUS_FILTERS = ["All statuses", "Needs review", "Approved", "Pending Validation", "Needs Clarification", "Rejected", "Archived"]
CAT_KEY = {v: k for k, v in config.DISPLAY_CATEGORY.items()}


def cat(x):
    return config.DISPLAY_CATEGORY.get(x, x)


# ------------------------------------------------------------------ dialogs
@st.dialog("Upload documents", width="large")
def _upload_dialog(ws, user):
    if not IS_BM(user):
        st.info("Only a Brand Manager can add brand documents.", icon=":material/lock:")
        return
    docs = q.list_documents(ws)
    files = st.file_uploader(f"PDF or Word documents (max {config.MAX_UPLOAD_MB:g} MB each)", type=["pdf", "docx"],
                             accept_multiple_files=True)
    a, b = st.columns(2)
    auth = a.selectbox("Source authority", ["Detect from file name"] + list(config.AUTHORITY_LEVELS),
                       help="When sources disagree, BrandCanon shows their authority and a person decides.")
    as_version = b.selectbox("Store as", ["New document"] + [f"New version of: {d['title']}" for d in docs])
    use_ai = st.toggle("Use live Gemini for extraction and classification", value=gs.enabled(), disabled=not gs.enabled())
    if not gs.enabled():
        st.caption("Live Gemini is off, so deterministic extraction is used and labelled.")
    st.caption("Extracted rules and facts start as Pending review. Nothing becomes brand policy until approved.")
    if st.button("Extract knowledge", type="primary", icon=":material/upload_file:", disabled=not files):
        msgs = []
        for f in files:
            title = as_version.split(": ", 1)[1] if as_version.startswith("New version") else None
            try:
                with st.spinner(f"Reading {f.name}…"):
                    r = di.ingest(ws, user["id"], f.name, f.getvalue(), None if auth.startswith("Detect") else auth,
                                  title=title, use_ai=use_ai)
            except (FileRejected, ParseError, PermissionError, ValueError) as e:
                msgs.append(("error", str(e)))
                continue
            if r.get("ai_error"):
                msgs.append(("error", f"{f.name}: Gemini extraction failed — {r['ai_error']} Deterministic extraction was used."))
            if r["status"] == "empty":
                msgs.append(("warning", f"{f.name}: no text could be extracted (it may be a scanned image). Nothing was added."))
                continue
            msgs.append(("success", f"{r['title']}: {r['rules']} rules, {r['facts']} facts and {r['terms']} terms extracted from "
                                    f"{r['passages']} passages, awaiting review."
                         + (f" {r['superseded_rules']} rules from the previous version were archived." if r["is_new_version"] else "")
                         + (f" {r['new_conflicts']} new conflict(s) recorded." if r["new_conflicts"] else "")))
            if r["injection_flags"]:
                msgs.append(("warning", f"{f.name} contains text that looks like instructions to an AI system. It was stored "
                                        "as data only and is never followed."))
            ss["con_doc"] = r["document_id"]
        ss["_upload_msgs"] = msgs
        st.rerun()
    if ss.get("ws_name") == demo.DEMO_NAME:
        st.divider()
        st.markdown("**NovaTech sample documents** <span class='bc-muted'>· fictional, extracted with deterministic logic so "
                    "the demo is reproducible</span>", unsafe_allow_html=True)
        if st.button("Upload the sample documents", icon=":material/library_add:"):
            res = c.run_action(demo.upload_samples, ws, user["id"])
            if res:
                ss["_upload_msgs"] = [("success", f"Uploaded {len(res)} sample documents: {sum(x['rules'] for x in res)} rules, "
                                                  f"{sum(x['facts'] for x in res)} facts, {sum(x['new_conflicts'] for x in res)} "
                                                  "conflicts recorded. Everything is awaiting review.")]
                st.rerun()


@st.dialog("Add a brand rule")
def _add_rule_dialog(ws, user):
    if not IS_BM(user):
        st.info("Only a Brand Manager can add brand rules.", icon=":material/lock:")
        return
    text = st.text_area("Rule", placeholder="e.g. Always write the product name as NovaTech X1, never Novatech or NT-X1.")
    a, b = st.columns(2)
    category = a.selectbox("Category", list(config.DISPLAY_CATEGORY), format_func=cat)
    scope = b.multiselect("Applies to", config.CHANNELS, default=["All content"])
    why = st.text_input("Why is it being added?", placeholder="e.g. Agreed at the 12 Nov brand review")
    approve = st.toggle("Approve it now", value=False, help="Otherwise it is saved as Pending review, like extracted rules.")
    st.caption("A manually added rule has no source document, so its source is shown as “added manually”.")
    if st.button("Save rule", type="primary", icon=":material/add:", disabled=not (text.strip() and why.strip())):
        rid = c.run_action(bc.add_rule, ws, user["id"], text, category, ", ".join(scope) or "All content", why, approve,
                           success="Rule added" + (" and approved" if approve else " — pending review"))
        if rid:
            ss["con_sel_rule"], ss["con_doc"] = rid, None
            ss["con_df_v"] = ss.get("con_df_v", 0) + 1
            st.rerun()


# ------------------------------------------------------------------ document library (cards)
def _doc_card(d, n_rules, selected):
    ext = (d.get("file_type") or "doc").upper().lstrip(".")[:4]
    status = d.get("review_status") or "Pending review"
    if d["status"] != "active":
        status = "Archived"
    border = f"box-shadow:0 0 0 2px {S.FOREST} inset;" if selected else ""
    return (f'<div style="{border}border-radius:16px;padding:2px">'
            f'<div class="bc-doc"><div class="ic">{c.esc(ext)}</div><div style="min-width:0"><div class="t" '
            f'style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{c.esc(d["title"])}</div>'
            f'<div class="m">{c.esc(ext)} · v{c.esc(d.get("version_label") or "1")} · {str(d.get("uploaded_at") or "")[:10]}</div>'
            f'</div></div><div style="margin-top:8px">{c.badge(status)}{c.badge(f"{n_rules} rules", "turquoise")}'
            f'{c.badge(f"authority {d["authority_rank"]}/5", "neutral")}</div></div>')


def _library(docs, rules):
    per_doc = Counter(r["document_id"] for r in rules if r["status"] not in ("Archived", "Rejected"))
    sel = ss.get("con_doc")
    c.card_title(f"Document library · {len(docs)}", "PDF and DOCX sources")
    cols = st.container(key="pair-docs").columns(4)
    with cols[0], c.card(key="card-doc-all", style="tint" if sel is None else "card"):
        st.markdown(f'<div style="font-family:{S.DISPLAY};font-weight:800;font-size:1.6rem;color:{S.TEXT}">{len(rules)}</div>'
                    f'<div class="bc-muted">knowledge items across all documents</div>', unsafe_allow_html=True)
        if st.button("All knowledge", key="doc_all", type="primary" if sel is None else "secondary", width="stretch"):
            ss["con_doc"] = None
            st.rerun()
    for i, d in enumerate(docs):
        with cols[(i + 1) % 4], c.card(key=f"card-doc-{d['id']}"):
            st.markdown(_doc_card(d, per_doc.get(d["id"], 0), sel == d["id"]), unsafe_allow_html=True)
            if st.button("Opened" if sel == d["id"] else "Open", key=f"od{d['id']}", width="stretch",
                         type="tertiary" if sel == d["id"] else "secondary", disabled=sel == d["id"]):
                ss["con_doc"], ss["con_sel_rule"] = d["id"], None
                st.rerun()


# ------------------------------------------------------------------ left: document information and preview
def _document_panel(ws, user, d):
    with c.card(key="card-docpanel"):
        st.markdown(f"<div class='bc-eyebrow'>Document</div><div style='font-family:{S.DISPLAY};font-weight:700;font-size:1.1rem;"
                    f"line-height:1.3'>{c.esc(d['title'])}</div>", unsafe_allow_html=True)
        rows = [("File", d["file_name"]), ("Type", (d.get("file_type") or "").upper().lstrip(".")),
                ("Version", d["version_label"]), ("Uploaded", str(d["uploaded_at"])[:10]),
                ("Pages / sections", d["page_count"]), ("Authority", f"{d['authority_level']} · {d['authority_rank']}/5"),
                ("Review status", d.get("review_status") or "Pending review")]
        st.markdown("<table class='bc-table bc-kv' style='font-size:.82rem;margin:8px 0'>" + "".join(
            f"<tr><td class='bc-muted' style='width:42%'>{k}</td><td>{c.esc(v)}</td></tr>" for k, v in rows) + "</table>",
            unsafe_allow_html=True)
        st.markdown(c.engine_tag(d["extraction_engine"] or ""), unsafe_allow_html=True)
        if d.get("review_note"):
            st.caption(f"Review note: {d['review_note']}")
        if d["injection_flags"]:
            st.markdown(c.badge(f"{d['injection_flags']} instruction-like phrase(s) stored as data", "amber"), unsafe_allow_html=True)
        if IS_BM(user) and d["status"] == "active":
            a, b = st.columns(2)
            if a.button("Approve source", key=f"da{d['id']}", disabled=d.get("review_status") == "Approved", width="stretch",
                        type="primary"):
                if c.run_action(bc.set_document_status, ws, user["id"], d["id"], "Approved", success=f"{d['title']} approved as a source"):
                    st.rerun()
            with b.popover("Reject", width="stretch"):
                why = st.text_input("Why is this not a trusted source?", key=f"drw{d['id']}")
                if st.button("Reject document", key=f"dr{d['id']}", disabled=not why.strip(), type="primary"):
                    if c.run_action(bc.set_document_status, ws, user["id"], d["id"], "Rejected", why, success="Document rejected"):
                        st.rerun()
            a, b = st.columns(2)
            if a.button("Archive", key=f"dar{d['id']}", width="stretch"):
                c.confirm("Archive this document?", f"**{c.esc(d['title'])}** stops being used for audits. Its rules and facts "
                          "stay in history.", "Archive", bc.archive_document, ws, user["id"], d["id"], success="Document archived")
            if b.button("Delete", key=f"dd{d['id']}", width="stretch"):
                c.confirm("Delete permanently?", f"Delete **{c.esc(d['title'])}**, all its versions, rules, facts and the conflicts "
                          "that referenced them. Audit history keeps its text. This cannot be undone.", "Delete permanently",
                          bc.delete_document, ws, user["id"], d["id"], success="Document deleted")
        pages = q.doc_pages(d["version_id"]) if d.get("version_id") else []
        if pages:
            st.markdown("<div class='bc-muted' style='margin:12px 0 4px'>Document preview · stored text</div>", unsafe_allow_html=True)
            pg = st.selectbox("Page", pages, key=f"pg_{d['id']}", label_visibility="collapsed")
            ps = q.passages_at(d["version_id"], pg)
            fake = {"doc_title": d["title"], "version_label": d["version_label"], "location": pg, "page_count": d["page_count"],
                    "file_name": d["file_name"], "authority_level": d["authority_level"], "authority_rank": d["authority_rank"],
                    "passages": ps}
            st.markdown(c.source_page(fake, ss.get("con_focus_passage")), unsafe_allow_html=True)
        cmp = bc.compare_versions(d["id"])
        if cmp:
            with st.expander(f"Compare v{cmp['previous']['version_label']} → v{cmp['current']['version_label']}"):
                for label, rows_, tone in [("Added", cmp["added"], "olive"), ("Removed", cmp["removed"], "red"),
                                           ("Unchanged", cmp["unchanged"], "neutral")]:
                    st.markdown(f"{c.badge(f'{label} · {len(rows_)}', tone)}", unsafe_allow_html=True)
                    for r in rows_[:8]:
                        st.markdown(f"<span style='font-size:.84rem'>{c.esc(r['text'])}</span>", unsafe_allow_html=True)


# ------------------------------------------------------------------ centre: extracted knowledge
def _knowledge(ws, user, rules, docs):
    with c.card(key="card-knowledge"):
        sel_doc = ss.get("con_doc")
        doc = next((d for d in docs if d["id"] == sel_doc), None)
        c.card_title("Extracted brand rules" if doc else "Brand knowledge", doc["title"] if doc else "all documents")
        f1, f2 = st.columns([1.2, 1])
        term = f1.text_input("Search", placeholder="Search rules, IDs or text", label_visibility="collapsed", key="con_q")
        status = f2.selectbox("Status", STATUS_FILTERS, key="con_status_sel", label_visibility="collapsed")
        category = ss.get("con_cat_pick")
        # "Needs review" matches the Overview count: unreviewed or flagged rules, plus rules with an open RuleProbe finding
        flagged = {x["rule"]["id"] for x in rule_probe.open_findings(ws)} if status == "Needs review" else set()
        view = [r for r in rules
                if (not doc or r["document_id"] == doc["id"])
                and (not category or cat(r["category"]) == category)
                and (status == "All statuses" or (status == "Needs review" and (r["status"] in ("Pending Validation", "Needs Clarification") or r["id"] in flagged))
                     or r["status"] == status)
                and (not term or term.lower() in f"{r['code']} {r['text']}".lower())]
        pending = [r for r in rules if r["status"] == "Pending Validation"]
        if IS_BM(user) and pending:
            with st.popover(f"Approve pending · {len(pending)}", icon=":material/done_all:"):
                st.markdown("Approve every pending rule and fact from documents at or above this source authority. Each one "
                            "can still be rejected or edited afterwards.")
                lvl = st.select_slider("Minimum authority", options=list(range(6)), value=3)
                if st.button("Approve all eligible", type="primary"):
                    n = c.run_action(bc.approve_all_pending, ws, user["id"], lvl)
                    if n is not None:
                        ss["_flash"] = f"Approved {n if n is not True else 0} rules"
                        st.rerun()
        if not view:
            c.empty("Nothing matches", "Change the filters, or upload documents to extract knowledge.")
            return None
        df = pd.DataFrame([{"ID": r["code"], "Statement": r["text"], "Category": cat(r["category"]), "Status": r["status"],
                            "Page": r["location"] or ("manual" if (r["extracted_by"] or "").startswith("manual") else "—")}
                           for r in view])
        ev = st.dataframe(df, hide_index=True, width="stretch", height=min(560, 38 + 35 * len(view)), on_select="rerun",
                          selection_mode="single-row", key=f"con_df_{ss.get('con_df_v', 0)}",
                          column_config={"Statement": st.column_config.TextColumn(width="large"),
                                         "ID": st.column_config.TextColumn(width="small"),
                                         "Page": st.column_config.TextColumn(width="small")})
        if ev.selection.rows:
            ss["con_sel_rule"] = view[ev.selection.rows[0]]["id"]
        st.caption(f"{len(view)} of {len(rules)} items. Select a row to see its source.")
        ids = [r["id"] for r in view]
        return ss.get("con_sel_rule") if ss.get("con_sel_rule") in ids else view[0]["id"]


# ------------------------------------------------------------------ right: source details and approval
def _detail(ws, user, r):
    with c.card(key="card-detail"):
        manual = (r["extracted_by"] or "").startswith("manual")
        st.markdown(f"<div class='bc-mono'>{c.esc(r['code'])} · version {r['rule_version']}</div>"
                    f"<div class='bc-specimen-rule'>{c.esc(r['text'])}</div>", unsafe_allow_html=True)
        st.markdown(c.badge(r["status"]) + c.badge(cat(r["category"]), "neutral") + c.badge(r["clarity"]), unsafe_allow_html=True)
        loc = r["location"]
        src = f"{r['doc_title']} · v{r['doc_version']} · {loc}" if loc else ""
        links = q.rule_links(r["id"])
        st.markdown(c.evidence_trail([
            ("Document", f"{r['doc_title']} v{r['doc_version']}" if r["doc_title"] else ("Added manually" if manual else "unknown"),
             "" if r["doc_title"] else "missing"),
            ("Passage", loc or "Source reference unavailable", "" if loc else "missing"),
            ("Rule", f"{r['code']} v{r['rule_version']}", ""),
            ("Tests", str(links["tests"]), ""), ("Findings", str(links["findings"]), ""),
            ("Decisions", str(links["decisions"]), "decision" if links["decisions"] else "")]), unsafe_allow_html=True)
        st.markdown("<span class='bc-muted'>Supporting passage</span>", unsafe_allow_html=True)
        if manual and not r["source_text"]:
            st.markdown(f"<div class='bc-quote'><i>Added manually ({c.esc(r['extracted_by'].split('·')[-1].strip())}). No source "
                        "document passage.</i></div>", unsafe_allow_html=True)
        else:
            st.markdown(c.quote(r["source_text"], src + ("" if r["doc_current"] else " · older version")), unsafe_allow_html=True)
        rows = [("Category", cat(r["category"])), ("Scope", r["scope"]), ("Source authority", r["authority_level"] or "—"),
                ("Extracted by", r["extracted_by"]),
                ("Approved", f"{r['approved_by_name']} · {r['approved_at'][:10]}" if r["approved_by_name"] else "not yet")]
        st.markdown("<table class='bc-table bc-kv' style='font-size:.84rem'>" + "".join(
            f"<tr><td class='bc-muted'>{k}</td><td>{c.esc(v)}</td></tr>" for k, v in rows) + "</table>", unsafe_allow_html=True)
        st.write("")
        if r.get("passage_id") and loc:
            with st.expander("View source page", icon=":material/description:"):
                st.markdown(c.source_page(q.source_page(r["passage_id"]), r["passage_id"]), unsafe_allow_html=True)
        if IS_BM(user):
            b = st.columns(3)
            for col, (label, s) in zip(b, [("Approve", "Approved"), ("Reject", "Rejected"), ("Archive", "Archived")]):
                if col.button(label, key=f"st_{s}_{r['id']}", disabled=r["status"] == s, width="stretch",
                              type="primary" if s == "Approved" and r["status"] != "Approved" else "secondary"):
                    if s == "Archived":
                        c.confirm("Archive this rule?", f"**{r['code']}** will no longer be used for audits.", "Archive",
                                  bc.set_rule_status, ws, user["id"], r["id"], s, success=f"{r['code']} archived")
                    elif c.run_action(bc.set_rule_status, ws, user["id"], r["id"], s, success=f"{r['code']}: {s}"):
                        st.rerun()
            with st.expander("Edit (saves a new version)", icon=":material/edit:"):
                nt = st.text_area("Rule text", r["text"], key=f"ed_{r['id']}")
                ns = st.multiselect("Scope", config.CHANNELS, default=[x for x in r["scope"].split(", ") if x in config.CHANNELS],
                                    key=f"sc_{r['id']}")
                why = st.text_input("Reason for the change", key=f"why_{r['id']}")
                if st.button("Save new version", disabled=not why.strip(), key=f"sv_{r['id']}", type="primary"):
                    if c.run_action(bc.edit_rule, ws, user["id"], r["id"], nt, why, ", ".join(ns) or "All content",
                                    success="New version saved"):
                        st.rerun()
        else:
            st.caption("Only a Brand Manager can approve, edit or reject rules.")
        a, b = st.columns(2)
        if a.button("Test in RuleProbe", icon=":material/biotech:", key=f"tp{r['id']}", type="tertiary"):
            c.go("ruleprobe", probe_rule=r["id"])
        if b.button("Show in graph", icon=":material/hub:", key=f"tg{r['id']}", type="tertiary"):
            c.go("graph", kg_q=r["code"])
        revs = q.rule_revisions(r["id"])
        if len(revs) > 1:
            with st.expander(f"Version history · {len(revs)} versions", icon=":material/history:"):
                for prev, cur in zip(revs, revs[1:]):
                    st.markdown(f"<span class='bc-mono'>v{prev['rule_version']} → v{cur['rule_version']} · "
                                f"{c.esc(cur['changed_by_name'] or 'system')} · {cur['created_at'][:10]}</span><br>"
                                f"<span class='bc-muted'>{c.esc(cur['reason'])}</span>", unsafe_allow_html=True)
                    st.markdown(c.diff(prev["text"], cur["text"]), unsafe_allow_html=True)


# ------------------------------------------------------------------ facts and terms
def _facts_tab(ws, user):
    facts = q.list_facts(ws)
    if not facts:
        c.empty("No product facts yet", "Upload a product specification to extract numeric facts with their qualifiers.")
        return
    for prod in sorted({f["product"] for f in facts}):
        with c.card():
            c.card_title(prod, "product facts")
            rows = [f for f in facts if f["product"] == prod]
            df = pd.DataFrame([{"Attribute": f["attribute"].title(), "Value": f"{f['value']:g} {f['unit']}", "Qualifier": f["qualifier"] or "—",
                                "Status": f["status"], "Source": f"{f['doc_title']} · v{f['doc_version']} · {f['location']}",
                                "Authority": f["authority_level"]} for f in rows])
            ev = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row", key=f"facts_{prod}")
            if ev.selection.rows:
                f = rows[ev.selection.rows[0]]
                st.markdown(c.quote(f["source_text"], f"{f['doc_title']} · v{f['doc_version']} · {f['location']}"), unsafe_allow_html=True)
                if IS_BM(user):
                    b = st.columns(4)
                    for col, (label, s) in zip(b, [("Approve", "Approved"), ("Reject", "Rejected"), ("Archive", "Archived")]):
                        if col.button(label, key=f"fs_{s}_{f['id']}", disabled=f["status"] == s, width="stretch"):
                            if c.run_action(bc.set_fact_status, ws, user["id"], f["id"], s, success=f"Fact {s.lower()}"):
                                st.rerun()
    st.caption("When sources disagree, the value from the source chosen in RuleProbe → Conflicts stays; the other becomes Superseded.")


def _terms_tab(ws, user):
    terms = q.list_terms(ws)
    with c.card():
        c.card_title("Terminology", "banned and preferred terms · exact matching on every audit, no AI")
        df = pd.DataFrame([{"term": t["term"], "kind": t["kind"], "replacement": t["replacement"]} for t in terms]
                          or [{"term": "", "kind": "prohibited", "replacement": ""}])
        edited = st.data_editor(df, num_rows="dynamic", width="stretch", hide_index=True, disabled=not IS_BM(user),
                                column_config={"term": "Term", "replacement": "Use instead",
                                               "kind": st.column_config.SelectboxColumn("Type", options=["prohibited", "preferred"], required=True)})
        if IS_BM(user) and st.button("Save term list", icon=":material/save:", type="primary"):
            n = c.run_action(bc.save_terms, ws, user["id"], edited.to_dict("records"))
            if n:
                ss["_flash"] = f"Saved {n} terms"
                st.rerun()


def _search_knowledge():
    q_ = (ss.get("con_ks") or "").strip()
    if q_ and q_ != ss.get("_con_last_ks"):
        ss["search_q"] = ss["_con_last_ks"] = q_
        ss["_con_search_go"] = True


def _header(ws, user):
    left, right = st.columns([2.2, 1.8], vertical_alignment="center")
    with left:
        c.header(None, "Brand Constitution", "Your organisation's approved brand knowledge.")
    with right, st.container(horizontal=True, horizontal_alignment="right", gap="small"):
        with st.popover("Search knowledge", icon=":material/search:"):
            st.text_input("Search every rule, passage, fact and decision", key="con_ks", on_change=_search_knowledge,
                          placeholder="e.g. battery, emoji, R004")
            st.caption("Press Enter to see results from every stored source.")
        if st.button("Add brand rule", icon=":material/add:", key="add_rule_btn", disabled=not IS_BM(user),
                     help=None if IS_BM(user) else "Only a Brand Manager can add rules."):
            _add_rule_dialog(ws, user)
        if st.button("Upload documents", icon=":material/upload_file:", type="primary", key="upload_btn"):
            ss["_open_upload"] = True


def render():
    ws, user = c.ctx()
    c.flash()
    if ss.pop("_con_search_go", False):
        c.go("search")
    # navigation from other screens
    if (rid := c.take("con_rule")) is not None:
        ss["con_sel_rule"], ss["con_doc"], ss["con_status_sel"], ss["con_cat_pick"] = rid, None, "All statuses", None
        ss["con_df_v"] = ss.get("con_df_v", 0) + 1
    if (st_f := c.take("con_status")) is not None:
        ss["con_status_sel"], ss["con_doc"], ss["con_cat_pick"] = st_f, None, None
        ss["con_df_v"] = ss.get("con_df_v", 0) + 1
    if (did := c.take("con_doc")) is not None:
        ss["con_doc"] = did
    open_upload = c.take("con_tab") == "Upload"

    _header(ws, user)
    for kind, msg in ss.pop("_upload_msgs", []):
        getattr(st, kind)(msg)
    if ss.pop("_open_upload", False) or open_upload:
        _upload_dialog(ws, user)

    docs = q.list_documents(ws, include_archived=True)
    rules = q.list_rules(ws)
    t = c.tabs(["Knowledge", "Product facts", "Terminology"], "con_tabs", "con_view")
    with t[0]:
        if not docs and not rules:
            c.empty("Your constitution is empty", "Upload brand guidelines, product specifications or policies (PDF or DOCX). "
                    "BrandCanon extracts candidate rules with their page references for your review.")
            if st.button("Upload documents", type="primary", icon=":material/upload_file:", key="up_empty"):
                _upload_dialog(ws, user)
            return
        _library(docs, rules)
        # knowledge categories with live counts
        counts = Counter(cat(r["category"]) for r in rules if r["status"] not in ("Archived", "Rejected"))
        opts = ["All categories"] + [f"{k} · {counts.get(k, 0)}" for k in CATS]
        cur = ss.get("con_cat_pick")
        default = next((o for o in opts if cur and o.startswith(cur + " ·")), "All categories")
        pick = st.pills("Knowledge categories", opts, default=default, key=f"con_cat_{ss.get('con_df_v', 0)}")
        ss["con_cat_pick"] = None if not pick or pick == "All categories" else pick.rsplit(" · ", 1)[0]
        doc = next((d for d in docs if d["id"] == ss.get("con_doc")), None)
        if doc:
            left, mid, right = st.container(key="wrap-con").columns([1, 1.4, 1.15])
            with left:
                _document_panel(ws, user, doc)
        else:
            mid, right = st.container(key="pair-con").columns([1.45, 1.1])
        with mid:
            rid = _knowledge(ws, user, rules, docs)
        with right:
            r = next((x for x in rules if x["id"] == rid), None)
            if r:
                _detail(ws, user, r)
            else:
                c.empty("Select an item", "Its source passage, page and review actions appear here.")
    with t[1]:
        _facts_tab(ws, user)
    with t[2]:
        _terms_tab(ws, user)
