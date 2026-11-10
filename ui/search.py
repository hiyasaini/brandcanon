"""Global search results — opened from the search box in the top bar."""
import streamlit as st

from modules import search as srch
from ui import components as c

ss = st.session_state
KIND = {"Brand rules": "rule", "Documents": "document", "Document passages": "document", "Product facts": "document",
        "Audit findings": "finding", "Decisions": "decision", "Content": "product"}


def render():
    ws, _ = c.ctx()
    query = ss.get("search_q", "")
    c.page_head("Search", f"Results for “{query}” across this workspace's stored records." if query else
                "Type in the search box at the top and press Enter.")
    res = srch.search(ws, query)
    if query and not res:
        c.empty("No matches", "Nothing stored in this workspace contains that text. Try a shorter word or a rule code such as R004.")
        return
    from ui import styles as S
    cols = st.columns(2)
    for i, (group, items) in enumerate(res.items()):
        color = S.ENTITY[KIND[group]][0]
        with cols[i % 2], c.card():
            c.card_title(group, f"{len(items)} result{'s' if len(items) != 1 else ''}")
            for j, it in enumerate(items):
                a, b = st.columns([5, 1], vertical_alignment="center")
                a.markdown(f'<div class="bc-row"><div class="ic" style="background:{color}33"><span style="width:9px;height:9px;'
                           f'border-radius:3px;background:{color};display:block"></span></div><div class="b"><div class="t">'
                           f'{c.esc(it["title"])}</div><div class="s">{c.esc(it["sub"])}</div></div></div>', unsafe_allow_html=True)
                if b.button("Open", key=f"sr{i}_{j}", type="tertiary"):
                    c.go(it["page"], **it["state"])
