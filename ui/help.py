"""Help & documentation — renders the project's own guides (no placeholder content)."""
import streamlit as st

import config
from ui import components as c

DOCS = [("User guide", "user_guide.md"), ("Demo walkthrough", "demo_script.md"), ("How it works", "architecture.md"),
        ("Known limitations", "limitations.md"), ("Test evidence", "testing.md")]
GLOSSARY = [
    ("Contradicted", "Approved evidence conflicts with the claim (for example, 15 hours vs the specification's 12)."),
    ("Unsupported", "No sufficient approved evidence exists for the claim. It is not called false."),
    ("Unverifiable", "The available information cannot settle the claim either way."),
    ("Ambiguous rule", "A strict and a lenient reading of the rule disagree on controlled examples. A potential finding "
                       "until a person reviews it."),
    ("Contradictory rules", "Two rules that apply to the same content pull in opposite directions."),
    ("Missing guidance", "No rule covers the chosen context."),
    ("Model uncertainty", "Repeated evaluations disagree with each other. This does not prove the rule is ambiguous."),
    ("Evidence trail", "The chain from a finding to the rule, the source document and page, the exact passage and any decision "
                       "about it. A missing link is shown as missing, never filled in."),
    ("Brand Knowledge Graph", "Every stored document, rule, test case, finding and decision as a node; every line is a stored "
                              "relationship. Click a node to open its record."),
    ("Outcome colours", "RuleProbe: green likely compliant, red potential violation, yellow uncertain, pink needs human review."),
    ("Precedent", "An earlier authorised decision on a similar claim. It is advice for the reviewer and never becomes a "
                  "brand rule by itself."),
]


def render():
    c.flash()
    c.header([st.session_state.get("ws_name", ""), "Help & documentation"], "Help & documentation",
             "How to use BrandCanon, what each finding means, and what the product does not do yet.")
    tabs = st.tabs(["Glossary"] + [t for t, _ in DOCS])
    with tabs[0]:
        st.markdown("<table class='bc-table'><tr><th>Term</th><th>Meaning</th></tr>" + "".join(
            f"<tr><td><b>{c.esc(k)}</b></td><td>{c.esc(v)}</td></tr>" for k, v in GLOSSARY) + "</table>", unsafe_allow_html=True)
    for tab, (_, fname) in zip(tabs[1:], DOCS):
        with tab:
            p = config.ROOT / "docs" / fname
            if p.exists():
                st.markdown(p.read_text())
            else:
                c.empty("Not found", f"docs/{fname} is missing from this installation.")
