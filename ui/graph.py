"""Brand Knowledge Graph — an interactive map of stored records and their relationships (dark investigation design).

Nodes and edges come from modules.knowledge_graph (stored records only). Clicking a node selects it through Plotly's
point selection (st.plotly_chart on_select) and the details panel shows that record with links to its screen.
"""
import plotly.graph_objects as go_
import streamlit as st

from modules import knowledge_graph as kg
from ui import components as c
from ui import styles as S

ss = st.session_state
CANVAS = "#14161B"
LAYOUTS = {"Force-directed": "force", "Circular": "circular", "Hierarchical": "hierarchical", "Grid": "grid"}
LABELLED = {"document", "rule", "product"}
REL_COLOR = {"contains": S.PINK, "tested_by": S.YELLOW, "produces": S.CORAL, "contradicts": S.CORAL, "concerns": S.TURQUOISE,
             "supported_by": S.PINK, "resolved_through": S.LAVENDER, "applies_to": S.LAVENDER, "about": S.MINT}


def legend_html(kinds=None):
    shapes = {"square": "border-radius:2px", "octagon": "border-radius:4px", "diamond": "transform:rotate(45deg);width:9px;height:9px",
              "circle": "border-radius:50%", "diamond-wide": "transform:rotate(45deg) scaleX(1.3);width:9px;height:9px",
              "hexagon": "border-radius:3px"}
    out = []
    for k, (col, sym, label) in S.ENTITY.items():
        if kinds and k not in kinds:
            continue
        out.append(f'<span class="bc-legend-chip"><i style="background:{col};{shapes[sym]}"></i>{c.esc(label)}</span>')
    return "<div>" + "".join(out) + "</div>"


def selected_from_state(key):
    """Node id clicked in the chart during the last interaction (read before the chart is redrawn)."""
    state = ss.get(key)
    try:
        pts = state["selection"]["points"] if state else []
    except (KeyError, TypeError):
        pts = []
    for p in pts:
        cd = p.get("customdata")
        if isinstance(cd, (list, tuple)):
            cd = cd[0] if cd else None
        if cd:
            return cd
    return None


def figure(G, pos, selected=None, height=620, labels="key", compact=False):
    near = set()
    if selected:
        for e in G["edges"]:
            if e["source"] == selected:
                near.add(e["target"])
            if e["target"] == selected:
                near.add(e["source"])
    fig = go_.Figure()
    # edges, one trace per relationship type (thin lines)
    for rel in kg.RELATIONS:
        xs, ys = [], []
        for e in G["edges"]:
            if e["rel"] != rel or e["source"] not in pos or e["target"] not in pos:
                continue
            (x0, y0), (x1, y1) = pos[e["source"]], pos[e["target"]]
            xs += [x0, x1, None]
            ys += [y0, y1, None]
        if xs:
            hot = selected is not None
            fig.add_trace(go_.Scatter(x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
                                      line=dict(width=0.9, color=REL_COLOR[rel]), opacity=0.16 if hot else 0.42, name=rel))
    if selected:   # the selected node's own edges, bright
        xs, ys = [], []
        for e in G["edges"]:
            if selected in (e["source"], e["target"]) and e["source"] in pos and e["target"] in pos:
                (x0, y0), (x1, y1) = pos[e["source"]], pos[e["target"]]
                xs += [x0, x1, None]
                ys += [y0, y1, None]
        fig.add_trace(go_.Scatter(x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
                                  line=dict(width=1.8, color="#FFFFFF"), opacity=0.75))
    # nodes, one trace per entity type; a node's size grows with how many records it connects to
    degree = {}
    for e in G["edges"]:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1
    for kind, (col, sym, label) in S.ENTITY.items():
        ns = [n for n in G["nodes"] if n["kind"] == kind and n["id"] in pos]
        if not ns:
            continue
        size = {"document": 20, "rule": 15, "case": 10, "finding": 12, "decision": 12, "product": 16}[kind]
        if compact:
            size += 6
        sizes, opac, lines, texts = [], [], [], []
        for n in ns:
            is_sel, is_near = n["id"] == selected, n["id"] in near
            grow = min(14, 2.2 * (degree.get(n["id"], 0) ** 0.5))
            sizes.append((size + grow) * (1.45 if is_sel else 1.0))
            opac.append(1.0 if (not selected or is_sel or is_near) else 0.25)
            lines.append(3 if is_sel else 1)
            show = labels == "all" or (labels == "key" and (kind in LABELLED or is_sel or is_near)) or compact
            texts.append(_short(n["label"]) if show else "")
        hover = [f"<b>{c.esc(_short(n['label'], 46))}</b><br><span style='color:{col}'>●</span> {c.esc(label)} · "
                 f"{degree.get(n['id'], 0)} connection{'s' if degree.get(n['id'], 0) != 1 else ''}<br>"
                 + "<br>".join(f"{c.esc(k)}: {c.esc(_short(str(v), 60))}" for k, v in list(n["detail"].items())[1:4])
                 + "<br><i>Click to open its record</i>" for n in ns]
        xs, ys = [pos[n["id"]][0] for n in ns], [pos[n["id"]][1] for n in ns]
        fig.add_trace(go_.Scatter(
            x=xs, y=ys, mode="markers+text", name=label,
            text=texts, textposition="top center",
            textfont=dict(color="#DDE1E8", size=10 if not compact else 11, shadow=f"0px 0px 3px {CANVAS}"),
            customdata=[n["id"] for n in ns], hovertext=hover, hoverinfo="text",
            marker=dict(symbol=sym, size=sizes, color=col, opacity=opac,
                        line=dict(width=[3 if w == 3 else 5 for w in lines],   # a soft halo ring in the node's own colour
                                  color=["#FFFFFF" if w == 3 else _rgba(col, 0.22 * o) for w, o in zip(lines, opac)])),
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=None))))
    fig.update_layout(height=height, margin=dict(l=4, r=4, t=4, b=4), paper_bgcolor=CANVAS, plot_bgcolor=CANVAS,
                      showlegend=False, dragmode="pan", hovermode="closest", clickmode="event+select",
                      font=dict(family="Inter, Helvetica Neue, Arial, sans-serif", color=S.DARK_TEXT),
                      hoverlabel=dict(bgcolor=S.DARK_PANEL, bordercolor="#3A3F4B", font=dict(color="#fff", size=12)),
                      uirevision="keep")
    fig.update_xaxes(visible=False, scaleanchor=None)
    fig.update_yaxes(visible=False)
    return fig


def _short(s, n=26):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def chart(G, key, layout_kind="force", height=620, labels="key", compact=False):
    """Draw the graph and return the selected node id (if any)."""
    ids = {n["id"] for n in G["nodes"]}
    clicked = selected_from_state(key)
    if clicked:
        ss[key + "_sel"] = clicked          # remembered across filter and layout changes, which redraw the chart
    sel = ss.get(key + "_sel")
    if sel not in ids:
        sel = None
    pos = kg.layout(G, layout_kind)
    fig = figure(G, pos, sel, height, labels, compact)
    st.plotly_chart(fig, key=key, on_select="rerun", selection_mode="points", width="stretch",
                    config={"displayModeBar": True, "displaylogo": False, "scrollZoom": True,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d", "toImage"]})
    return sel


def _rgba(hex_, a):
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a:.2f})"


def _overview(G):
    """What the visible graph holds, before anything is selected: records per type and the most connected records."""
    if not G["nodes"]:
        return
    kinds = {}
    for n in G["nodes"]:
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    rows = "".join(f"<div class='r'><div class='l'><span style='color:{S.ENTITY[k][0]}'>●</span> {c.esc(S.ENTITY[k][2])}</div>"
                   f"<div class='b'><i style='width:{v / max(kinds.values()) * 100:.0f}%;background:{S.ENTITY[k][0]}'></i></div>"
                   f"<div class='n'>{v}</div></div>" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]) if k in S.ENTITY)
    st.markdown(f"<div class='bc-kg-h'>In this view</div><div class='bc-rank dk'>{rows}</div>", unsafe_allow_html=True)
    degree = {}
    for e in G["edges"]:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1
    by_id = {n["id"]: n for n in G["nodes"]}
    hubs = [(by_id[i], d) for i, d in sorted(degree.items(), key=lambda kv: -kv[1]) if i in by_id][:5]
    if hubs:
        st.markdown("<div class='bc-kg-h'>Most connected</div><div class='bc-rank dk'>" + "".join(
            f"<div class='r' title='{c.esc(n['label'])}'><div class='l'><span style='color:{S.ENTITY[n['kind']][0]}'>●</span> "
            f"{c.esc(_short(n['label'], 40))}</div><div class='b'><i style='width:{d / hubs[0][1] * 100:.0f}%;"
            f"background:{S.ENTITY[n['kind']][0]}'></i></div><div class='n'>{d}</div></div>" for n, d in hubs)
            + "</div>", unsafe_allow_html=True)


def details(G, nid, key):
    """Right-hand details panel for a selected node: its stored fields, its connections and where to open it."""
    by_id = {n["id"]: n for n in G["nodes"]}
    n = by_id.get(nid)
    if not n:
        st.markdown("<div class='bc-muted'>Click any node to see its record, its connections and where it comes from.</div>",
                    unsafe_allow_html=True)
        _overview(G)
        return
    col, _, label = S.ENTITY[n["kind"]]
    st.markdown(f"<span class='bc-badge' style='background:{col}26;color:{col}'>{c.esc(n['detail'].get('Type', label))}</span>",
                unsafe_allow_html=True)
    st.markdown(f"<div style='font-family:{S.DISPLAY};font-weight:700;font-size:1.05rem;color:#fff;margin:2px 0 8px'>"
                f"{c.esc(n['label'])}</div>", unsafe_allow_html=True)
    rows = "".join(f"<tr><td style='color:{S.DARK_MUTED};width:38%'>{c.esc(k)}</td><td>{c.esc(v)}</td></tr>"
                   for k, v in list(n["detail"].items())[1:])
    st.markdown(f"<table class='bc-table bc-kv' style='font-size:.8rem'>{rows}</table>",
                unsafe_allow_html=True)
    for i, (text, page, state) in enumerate(n["open"]):
        if st.button(text, key=f"{key}_open{i}", type="primary" if i == 0 else "secondary", width="stretch",
                     icon=":material/open_in_new:"):
            c.go(page, **state)
    nb = kg.neighbours(G, nid)
    if nb:
        st.markdown(f"<div class='bc-muted' style='margin:14px 0 6px'>Connections · {len(nb)}</div>", unsafe_allow_html=True)
        groups = {}
        for rel, arrow, m in nb:
            groups.setdefault((rel, arrow), []).append(m)
        for (rel, arrow), ms in groups.items():
            chips = "".join(f"<span style='display:inline-flex;align-items:center;gap:5px;background:#20232B;border-radius:6px;"
                            f"padding:1px 7px;margin:0 4px 4px 0;font-size:.74rem'><i style='width:7px;height:7px;border-radius:2px;"
                            f"background:{S.ENTITY[m['kind']][0]}'></i>{c.esc(_short(m['label'], 30))}</span>" for m in ms[:12])
            more = f"<span class='bc-muted' style='font-size:.74rem'>+{len(ms) - 12} more</span>" if len(ms) > 12 else ""
            st.markdown(f"<div style='font-size:.76rem;color:{S.DARK_MUTED};margin:6px 0 3px'>{c.esc(rel)} {arrow} "
                        f"<b style='color:#fff'>{len(ms)}</b></div><div>{chips}{more}</div>", unsafe_allow_html=True)

def _clear():
    ss.pop("kg_chart_sel", None)
    ss["kg_focus"] = False


def render():
    ws, _ = c.ctx()
    S.dark()
    c.flash()
    c.page_head("Brand Knowledge Graph", "How your documents, rules, tests, findings and decisions connect — every node is a "
                "stored record.")
    G = kg.build(ws)
    if not G["nodes"]:
        c.empty("Nothing to map yet", "Upload brand documents in Brand Constitution. Rules, tests, findings and decisions appear "
                "here as they are created.")
        return
    with c.card(key="panel-kgctl"):
        a, b, d = st.container(key="pair-kgc1").columns([1.5, 2.6, 1.3], vertical_alignment="bottom")
        query = a.text_input("Search the graph", key="kg_q", placeholder="e.g. battery, R004, Approved")
        kind_labels = {S.ENTITY[k][2]: k for k in kg.KINDS}
        chosen = b.pills("Entities", list(kind_labels), selection_mode="multi", default=list(kind_labels), key="kg_kinds")
        lay = d.selectbox("Layout", list(LAYOUTS), key="kg_layout")
        e1, e2, e3 = st.container(key="pair-kgc2").columns([2.6, 1.2, 1.2], vertical_alignment="bottom")
        rel_labels = {v: k for k, v in kg.RELATIONS.items()}
        rels = e1.multiselect("Relationships", list(rel_labels), default=list(rel_labels), key="kg_rels")
        labels = e2.selectbox("Labels", ["Key entities", "All", "None"], key="kg_labels")
        focus_on = e3.toggle("Focus on selection", key="kg_focus", help="Show only the selected node and its direct connections.")
    kinds = [kind_labels[x] for x in (chosen or [])]
    sub = kg.subgraph(G, kinds, [rel_labels[x] for x in rels], query=query.strip())
    sel_prev = selected_from_state("kg_chart") or ss.get("kg_chart_sel")
    if focus_on and sel_prev:
        sub = kg.subgraph(sub, kinds, [rel_labels[x] for x in rels], focus=sel_prev, depth=1)
    if query.strip() and not sub["seeds"]:
        st.info(f"No node matches “{query}”. Showing nothing — clear the search to see the whole graph.", icon=":material/search_off:")
    left, right = st.container(key="wrap-kg").columns([3.1, 1.15])
    with left, c.card(key="panel-kgcanvas"):
        st.markdown(legend_html(set(kinds)), unsafe_allow_html=True)
        if not sub["nodes"]:
            c.empty("No nodes", "Every node is filtered out. Choose more entities or relationships.")
            sel = None
        else:
            sel = chart(sub, "kg_chart", LAYOUTS[lay], 640, {"Key entities": "key", "All": "all", "None": "none"}[labels])
        st.caption(f"{len(sub['nodes'])} of {len(G['nodes'])} nodes · {len(sub['edges'])} relationships · drag to pan, scroll or "
                   "use + / − to zoom, double-click to reset.")
    with right, c.card(key="panel-kgdetail"):
        st.markdown("#### Details")
        details(sub, sel, "kgd")
        if sel:
            st.button("Clear selection", key="kg_clear", type="tertiary", icon=":material/close:", on_click=_clear)
