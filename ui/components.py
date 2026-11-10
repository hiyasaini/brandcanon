"""Reusable UI pieces for the BrandCanon brand intelligence workspace.

UI code calls business modules only — never the database or Gemini directly. Every component renders real stored
records; nothing here invents sources, page numbers, metrics or decisions.
"""
import difflib
import html

import plotly.graph_objects as go_
import streamlit as st

from ui import styles as S

ss = st.session_state

STATUS_TONE = {
    "Approved": "olive", "Pending Validation": "amber", "Pending review": "amber", "Rejected": "neutral",
    "Needs Clarification": "amber", "Archived": "neutral", "Superseded": "neutral", "In review": "terracotta",
    "Draft": "neutral", "Changes requested": "amber", "Escalated": "red", "open": "amber", "resolved": "olive",
    "Ambiguous": "amber", "Clear": "olive", "In conflict": "red", "Missing guidance": "amber", "Uncertain": "yellow",
    "Untested": "neutral", "Accepted as written": "olive", "Changes needed": "red", "Review suggested": "amber",
    "No issues found": "olive", "Ambiguous rule": "amber", "Contradictory rules": "red", "Model uncertainty": "pink",
    "Clear rule": "olive", "Contradicted": "red", "Unsupported": "amber", "Unverifiable": "pink", "Verified": "olive",
    "Violation": "red", "Needs review": "amber", "high": "red", "medium": "amber", "low": "lavender", "info": "olive",
    "accepted": "olive", "edited": "olive", "dismissed": "neutral", "Finding upheld": "terracotta",
    "Finding overridden": "lavender", "draft": "neutral", "saved": "lavender", "in_review": "amber", "approved": "olive",
    "rule_updated": "olive", "Likely compliant": "olive", "Potential violation": "red", "Needs human review": "pink",
}
SEV_MARK = {"high": 1, "medium": 1, "low": 1}
INVESTIGATION_LABEL = {"draft": "Draft (not saved)", "saved": "Saved", "in_review": "Sent for human review",
                       "approved": "Interpretation approved", "rule_updated": "Rule updated after authorisation"}


def esc(x):
    return html.escape(str(x if x is not None else ""))


# ------------------------------------------------------------------ navigation helpers
def go(page_key, **state):
    """Navigate to another screen, opening a specific record/tab (state is read by the destination page)."""
    for k, v in state.items():
        ss[k] = v
    st.switch_page(ss.pages[page_key])


def nav_button(label, page_key, key, state=None, icon=None, kind="secondary", width="content", help=None):
    if st.button(label, key=key, icon=icon, type=kind, width=width, help=help):
        go(page_key, **(state or {}))


# ------------------------------------------------------------------ page header
def header(crumbs, title, subtitle=""):
    """Page title and supporting line (the workspace is shown in the top bar)."""
    st.markdown(f'<div class="bc-head"><div class="bc-title">{esc(title)}</div><div class="bc-sub">{esc(subtitle)}</div></div>',
                unsafe_allow_html=True)


def page_head(title, subtitle, actions=None, crumb=None):
    """Header with right-aligned actions: actions = [(label, callable_or_page, kind, icon), ...]."""
    acts = actions or []
    if not acts:
        header(None, title, subtitle)
        return
    left, right = st.columns([2.4, 1.6], vertical_alignment="center")
    with left:
        header(None, title, subtitle)
    with right, st.container(horizontal=True, horizontal_alignment="right", gap="small"):
        for i, (label, target, kind, icon) in enumerate(acts):
            if st.button(label, key=f"pa_{title}_{i}", type=kind, icon=icon):
                if callable(target):
                    target()
                else:
                    go(*target) if isinstance(target, tuple) else go(target)


# ------------------------------------------------------------------ cards
_card_n = [0]


def reset_cards():
    _card_n[0] = 0


def card(height=None, key=None, style="card"):
    """A rounded panel: style 'card' (white), 'tint' (light sage) or 'forest' (dark green feature card)."""
    _card_n[0] += 1
    kw = {"border": True, "key": key or f"{style}-{_card_n[0]}"}
    if height:
        kw["height"] = height
    return st.container(**kw)


# ------------------------------------------------------------------ small pieces
def code(text):
    """A rule ID, version or document reference."""
    return f'<span class="bc-code">{esc(text)}</span>'


def badge(text, tone=None):
    bg, fg = S.TONES.get(tone or STATUS_TONE.get(text, "neutral"), S.TONES["neutral"])
    return f'<span class="bc-badge" style="background:{bg};color:{fg}">{esc(text)}</span>'


ICONS = {  # simple line icons (24px grid) used on metric cards
    "rules": '<path d="M5 4h10l4 4v12H5z M15 4v4h4 M8 12h8 M8 16h6"/>',
    "review": '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
    "audit": '<path d="M4 5h16v11H8l-4 4z M8 9h8 M8 12h5"/>',
    "conflict": '<path d="M12 3l9 16H3z M12 9v4 M12 16v.5"/>',
    "repeat": '<path d="M4 9a8 8 0 0 1 14-3l2 2 M20 15a8 8 0 0 1-14 3l-2-2 M20 4v4h-4 M4 20v-4h4"/>',
    "probe": '<circle cx="10" cy="10" r="6"/><path d="M15 15l5 5"/>',
    "time": '<circle cx="12" cy="12" r="8"/><path d="M12 7v5h4"/>',
    "decision": '<path d="M5 12l4 4 10-10"/>',
}


def _icon(name, color):
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round">{ICONS.get(name, ICONS["rules"])}</svg>')


def metric(label, value, note="", tone="", icon=None):
    is_text = not str(value).replace(".", "", 1).replace("%", "").replace(",", "").replace(" min", "").replace(" h", "").lstrip("-").isdigit()
    cls = f"{tone} txt" if is_text else tone
    color = "#FFFFFF" if "forest" in tone else S.FOREST
    ic = f'<div class="ic">{_icon(icon, color)}</div>' if icon else '<i class="dot"></i>'
    st.markdown(f'<div class="bc-metric {cls}"><div class="top"><div class="l">{esc(label)}</div>{ic}</div>'
                f'<div class="v">{esc(value)}</div><div class="n">{esc(note)}</div></div>', unsafe_allow_html=True)


def metric_link(label, value, note, tone, page_key, state, key, link_label="View", icon=None):
    """Metric card whose value is computed by the caller from the database; the button opens the filtered page."""
    with st.container(key=f"ml-{key}"):
        metric(label, value, note, tone, icon)
        if st.button(link_label, key=key, type="tertiary", icon=":material/arrow_outward:", icon_position="right"):
            go(page_key, **state)


def card_title(title, note=""):
    st.markdown(f'<div class="bc-card-title">{esc(title)}{f"<small>{esc(note)}</small>" if note else ""}</div>',
                unsafe_allow_html=True)


def legend(items):
    """items: [(label, colour)]"""
    return '<div class="bc-legend">' + "".join(f'<span><i style="background:{c}"></i>{esc(t)}</span>' for t, c in items) + "</div>"


def empty(title, text):
    st.markdown(f'<div class="bc-empty"><b>{esc(title)}</b>{esc(text)}</div>', unsafe_allow_html=True)


def illustrative(text="Illustrative demo records: NovaTech is fictional and its history was generated through the real "
                      "pipeline and backdated. Numbers below are computed from those stored records."):
    st.markdown(f'<div class="bc-illustrative">{esc(text)}</div>', unsafe_allow_html=True)


def doc_row(d):
    ext = (d.get("file_type") or "doc").upper()[:4]
    meta = f"v{d.get('version_label') or '1'} · {str(d.get('uploaded_at') or d.get('created_at') or '')[:10]} · authority {d['authority_rank']}/5"
    return (f'<div class="bc-doc"><div class="ic">{esc(ext)}</div><div><div class="t">{esc(d["title"])}</div>'
            f'<div class="m">{esc(meta)}</div></div></div>')


def quote(text, source):
    if not text:
        return '<div class="bc-quote"><i>Source reference unavailable — no stored passage supports this item.</i></div>'
    return f'<div class="bc-quote">“{esc(text)}”<div class="src">{esc(source) or "Source not recorded"}</div></div>'


evidence = quote  # older name


def evidence_trail(nodes):
    """The signature evidence trail: content → rule → source → passage → decision.

    nodes: list of (key, value, kind) where kind is '', 'missing' or 'decision'. A missing link is shown, not hidden.
    """
    parts = []
    for i, (k, v, kind) in enumerate(nodes):
        if i:
            parts.append('<div class="link"></div>')
        cls = f"{kind} k-{str(k).lower().split()[0]}"
        parts.append(f'<div class="node {cls}"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>')
    return f'<div class="bc-trail">{"".join(parts)}</div>'


def finding_trail(f, decision=None):
    """Evidence trail for an audit finding, from stored fields only."""
    nodes = [("Content", f"“{(f.get('quote') or 'whole text')[:60]}”", "")]
    if f.get("rule_code"):
        nodes.append(("Rule", f"{f['rule_code']}" + (f" v{f['rule_version']}" if f.get("rule_version") else ""), ""))
    src = f.get("evidence_source") or ""
    if f.get("evidence_text"):
        nodes.append(("Source", src or "recorded passage", ""))
    else:
        nodes.append(("Source", "No approved evidence found" if f.get("classification") in ("Unsupported", "Unverifiable")
                      else "Source reference unavailable", "missing"))
    if decision:
        nodes.append(("Decision", f"{decision['decision']} · {decision['reviewer_name']} · {decision['created_at'][:10]}", "decision"))
    return evidence_trail(nodes)


def timeline(events):
    """events: list of dicts with at, label, detail, tone ('terracotta' | 'olive' | 'amber' | 'red' | 'neutral')."""
    if not events:
        return '<div class="bc-muted">No events recorded yet.</div>'
    rows = "".join(f'<div class="ev t-{esc(e.get("tone", "neutral"))}"><div class="w">{esc(str(e["at"])[:16].replace("T", " "))}'
                   f'{" · " + esc(e["who"]) if e.get("who") else ""}</div><div class="a">{esc(e["label"])}</div>'
                   f'{"<div class=d>" + esc(e["detail"][:160]) + "</div>" if e.get("detail") else ""}</div>' for e in events)
    return f'<div class="bc-tl">{rows}</div>'


def highlighted(text, findings, focus=None):
    """Audited text with marked phrases and numbered flags. `focus` (finding index) emphasises one phrase."""
    spans = sorted([(f["span_start"], f["span_end"], i, f["severity"]) for i, f in enumerate(findings)
                    if f.get("span_end") and f["span_end"] > f["span_start"] and f["severity"] in SEV_MARK
                    and f.get("disposition", "open") != "dismissed"])
    out, pos = [], 0
    for s, e, i, sev in spans:
        if s < pos:
            continue
        on = " on" if focus == i else ""
        out += [esc(text[pos:s]), f'<mark class="m-{sev}{on}" title="Finding {i + 1} ({sev})">{esc(text[s:e])}</mark>'
                                  f'<sup class="flag f-{sev}">{i + 1}</sup>']
        pos = e
    out.append(esc(text[pos:]))
    return f'<div class="bc-text{" focus" if focus is not None else ""}">' + "".join(out) + "</div>"


def source_page(page, focus_id=None):
    """A stored document page drawn as paper, with the cited passage highlighted. Built only from stored passages."""
    if not page:
        return quote("", "")
    body = "".join(f'<p class="{"cited" if p["id"] == focus_id else ""}">{esc(p["text"])}</p>' for p in page["passages"])
    of = f" of {page['page_count']}" if page.get("page_count") else ""
    return (f'<div class="bc-page"><div class="hd"><span>{esc(page["doc_title"])} · v{esc(page["version_label"])}</span>'
            f'<span>{esc(page["location"])}{of}</span></div>{body}<div class="ft">{esc(page["file_name"])} · '
            f'{esc(page["authority_level"])} · authority {page["authority_rank"]}/5</div></div>')


def before_after(original, current, issues_before, issues_after):
    """The payoff view: the first draft and the current revision side by side, with the issue count before and after."""
    return (f'<div class="bc-ba"><div class="side before"><div class="k">First draft · {issues_before} issue'
            f'{"s" if issues_before != 1 else ""}</div><div class="t">{esc(original)}</div></div>'
            f'<div class="arrow" aria-hidden="true">→</div><div class="side after"><div class="k">Current revision · '
            f'{issues_after} issue{"s" if issues_after != 1 else ""}</div><div class="t">{esc(current)}</div></div></div>')


def diff(a, b):
    aw, bw = (a or "").split(), (b or "").split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, aw, bw).get_opcodes():
        if op == "equal":
            out.append(esc(" ".join(aw[i1:i2])))
        if op in ("delete", "replace"):
            out.append(f"<del>{esc(' '.join(aw[i1:i2]))}</del>")
        if op in ("insert", "replace"):
            out.append(f"<ins>{esc(' '.join(bw[j1:j2]))}</ins>")
    return '<div class="bc-text bc-diff">' + " ".join(out) + "</div>"


# ------------------------------------------------------------------ actions, feedback, dialogs
def run_action(fn, *args, success=None, **kwargs):
    """Call a business function; show a meaningful error instead of a stack trace. Returns the result or None."""
    try:
        with st.spinner("Working…"):
            res = fn(*args, **kwargs)
        if success:
            ss["_flash"] = success
        return res if res is not None else True
    except (ValueError, PermissionError) as e:
        error(str(e))
    except Exception as e:  # noqa: BLE001 — unexpected: show it, keep the app usable
        error(f"Something went wrong: {e}")
    return None


def error(msg):
    st.error(msg, icon=":material/error:")


def flash():
    msg = ss.pop("_flash", None)
    if msg:
        st.toast(msg, icon=":material/check_circle:")


def confirm(title, body, label, fn, *args, success=None, danger=True, **kwargs):
    """Open a confirmation dialog for a destructive or consequential action."""
    @st.dialog(title)
    def _dlg():
        st.markdown(body)
        a, b = st.columns(2)
        if a.button(label, type="primary", width="stretch", key=f"cf_{title}"):
            if run_action(fn, *args, success=success, **kwargs):
                st.rerun()
        if b.button("Cancel", width="stretch", key=f"cx_{title}"):
            st.rerun()
    _dlg()


def plot_layout(fig, height=300, dark=False):
    """House chart style: recessive grid and axes, legend above the plot, white tooltip card, rounded bar ends."""
    fg, grid, muted = (S.DARK_TEXT, "#262A33", "#A7ADB8") if dark else (S.TEXT, S.LINE_SOFT, S.MUTED)
    legend_on = sum(1 for t in fig.data if t.showlegend is not False) > 1 and fig.layout.showlegend is not False
    fig.update_layout(height=height, margin=dict(l=4, r=8, t=34 if legend_on else 10, b=4), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, Helvetica Neue, Arial, sans-serif", color=fg, size=12),
                      legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom", font=dict(size=11, color=muted),
                                  itemsizing="constant", bgcolor="rgba(0,0,0,0)", traceorder="normal"),
                      bargap=0.38, barcornerradius=4, colorway=S.CHART_SEQ,
                      hoverlabel=dict(bgcolor=S.DARK_PANEL if dark else "#FFFFFF", bordercolor="#3A3F4B" if dark else S.BORDER,
                                      font=dict(color="#fff" if dark else S.TEXT, size=12, family="Inter, sans-serif"),
                                      align="left"))
    fig.update_xaxes(showgrid=False, zeroline=False, showline=True, linecolor=grid, tickangle=0, automargin=True,
                     tickfont=dict(color=muted, size=11), ticks="")
    fig.update_yaxes(gridcolor=grid, zeroline=False, showline=False, tickfont=dict(color=muted, size=11), automargin=True)
    return fig


def week_ticks(weeks):
    """ISO weeks ('2026-W41') → (hover label, two-line tick text with the Monday's date)."""
    from datetime import date as _d
    keys, ticks = [], []
    for w in weeks:
        y, n = str(w).split("-W")
        mon = _d.fromisocalendar(int(y), int(n), 1)
        keys.append(f"W{int(n)} · {mon.day} {mon:%b}")
        ticks.append(f"W{int(n)}<br><span style='font-size:10px'>{mon.day} {mon:%b}</span>")
    return keys, ticks


def weekly_bars(weeks, series, height=260, unit="finding"):
    """Stacked weekly columns with a total above each week. series: [(name, colour, [values per week])]."""
    keys, ticks = week_ticks(weeks)
    fig = go_.Figure()
    shown = [(n, col, v) for n, col, v in series if any(v)]
    for name, col, vals in shown:
        fig.add_trace(go_.Bar(x=keys, y=vals, name=name, marker=dict(color=col, line=dict(color="#FFFFFF", width=1.5)),
                              hovertemplate=f"{esc(name)}: %{{y}}<extra></extra>"))
    totals = [sum(v[i] for _, _, v in shown) for i in range(len(keys))]
    fig.add_trace(go_.Scatter(x=keys, y=totals, mode="text", text=[str(t) if t else "" for t in totals], textposition="top center",
                              textfont=dict(size=11, color=S.TEXT, family="Inter, sans-serif"), showlegend=False,
                              hovertemplate=f"<b>Total: %{{y}} {unit}s</b><extra></extra>", cliponaxis=False))
    top = max(totals or [0])
    fig.update_layout(barmode="stack", hovermode="x unified", bargap=0.42)
    fig.update_xaxes(tickvals=keys, ticktext=ticks, type="category")
    fig.update_yaxes(range=[0, top * 1.22 + 0.5], dtick=max(1, round(top / 4)) if top else 1, rangemode="tozero")
    return plot_layout(fig, height)


def hbars(labels, values, colors, height=None, total=None, hover=None):
    """Horizontal bars, largest first, labelled 'n · share%' at the bar end."""
    total = total if total is not None else (sum(values) or 1)
    text = [f"<b>{v}</b>  <span style='color:{S.MUTED}'>{v / total:.0%}</span>" if total else str(v) for v in values]
    fig = go_.Figure(go_.Bar(x=values, y=labels, orientation="h", marker=dict(color=colors), text=text, textposition="outside",
                             cliponaxis=False, hovertext=hover or labels,
                             hovertemplate="%{hovertext}: <b>%{x}</b><extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=12, color=S.TEXT))
    fig.update_xaxes(showticklabels=False, showline=False, range=[0, max(values or [1]) * 1.32 + 0.1])
    fig.update_layout(bargap=0.42)
    return plot_layout(fig, height or 48 + 38 * len(labels))


def rank_rows(rows, color, values=None, scale=None):
    """A ranked list with proportional bars. rows: [(label_html, shown_value, full_text_for_title)] — label_html must be escaped.
    values: the numbers the bars are drawn from (defaults to the shown values)."""
    if not rows:
        return ""
    vals = values if values is not None else [n for _, n, _ in rows]
    top = scale or max(vals) or 1
    return '<div class="bc-rank">' + "".join(
        f'<div class="r" title="{esc(t)}"><div class="l">{lab}</div><div class="b"><i style="width:{v / top * 100:.0f}%;'
        f'background:{color}"></i></div><div class="n">{esc(str(n))}</div></div>' for (lab, n, t), v in zip(rows, vals)) + "</div>"


def chart_stat(items):
    """A one-line row of headline figures above a chart. items: [(value, label)]."""
    return '<div class="bc-cstat">' + "".join(f"<span><b>{esc(str(v))}</b>{esc(l)}</span>" for v, l in items) + "</div>"


def week_label(w):
    """'2026-W41' → 'W41' (charts span a few weeks, so the year only adds clutter)."""
    return "W" + str(w).split("W")[-1]


def ctx():
    """(workspace_id, signed-in user)."""
    return ss["ws"], ss["user"]


def take(key, default=None):
    """Read and clear a one-shot navigation value set by another page."""
    return ss.pop(key, default)


def gs_enabled():
    from services import gemini_service
    return gemini_service.enabled()


def tabs(names, key, nav_key=None):
    """Stateful tabs: another page can open a specific tab by setting session_state[nav_key] before navigating."""
    want = take(nav_key) if nav_key else None
    if want in names:
        ss[key] = want
    elif ss.get(key) not in names:
        ss[key] = names[0]
    return st.tabs(names, key=key, on_change="rerun")


# ------------------------------------------------------------------ AI provenance
def engine_tag(label):
    """Badge saying where a result came from: live Gemini, deterministic logic, demo fallback, or a Gemini failure."""
    from services import gemini_service as gs
    src = gs.source_of(label)
    tone = {"live": "olive", "deterministic": "neutral", "demo": "amber", "failed": "red"}[src]
    head = {"live": "Live Gemini", "deterministic": "Deterministic logic", "demo": "Demo fallback",
            "failed": "Gemini failed"}[src]
    rest = (label or "").strip()
    if rest.startswith(head) or head.startswith(rest):
        rest = rest[len(head):].strip(" ·—:") if rest.startswith(head) else ""
    extra = f'<span class="bc-muted" style="font-size:.78rem">{esc(rest)}</span>' if rest else ""
    return badge(head, tone) + extra


def engine_alert(label, detail=None):
    """If a result was produced because Gemini failed, say so plainly (with the safe error message)."""
    from services import gemini_service as gs
    if gs.is_failure(label):
        msg = detail or gs.last_error() or "See Settings → AI and privacy for details."
        st.error(f"**Gemini did not produce this result.** {label}. {msg} "
                 "The checks shown were run by BrandCanon's deterministic logic instead.", icon=":material/cloud_off:")
