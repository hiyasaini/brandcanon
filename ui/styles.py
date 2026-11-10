"""BrandCanon design system — Premium Brand Intelligence Workspace.

Two connected design languages share one shell:
  * light — a sage frame around a large white rounded workspace with white cards (Overview, Constitution, Content
    Intelligence, Decision Memory, Governance);
  * dark  — a charcoal investigation canvas with thin lines and coloured nodes (RuleProbe, Brand Knowledge Graph).
Sage and forest green carry the brand. Turquoise, lavender, coral, yellow and pink are reserved for entity types
(documents, rules, test cases, findings, decisions) so the same colour means the same thing on every screen.

Palette values are the brief's exact tokens. Where a token is too light for small text on white (secondary text #858D86
is 3.4:1), a darker shade of the same hue is used for small text so labels meet WCAG AA.
"""
import streamlit as st

# ---------------------------------------------------------------- brief tokens (exact)
SAGE = "#52665C"          # main sage background (frame)
SAGE_LIGHT = "#E6EBE5"    # light sage surfaces
FOREST = "#263A32"        # dark forest: primary actions, emphasis
GREEN = "#718A7B"         # primary green
MINT = "#B9CDBD"          # soft mint
WHITE = "#FFFFFF"
TEXT = "#242824"          # main text
TEXT_2 = "#858D86"        # secondary text (large text / decoration)
BORDER = "#E6E9E5"        # light borders
DARK_BG = "#101114"       # dark workspace
DARK_PANEL = "#191B22"    # dark panel
TURQUOISE = "#56C9C1"
LAVENDER = "#AD83EE"
CORAL = "#F17D83"
YELLOW = "#F0CF72"
PINK = "#E79BD0"

# ---------------------------------------------------------------- accessible shades and tints (same hues)
MUTED = "#646C65"         # small secondary text on white (5.4:1)
GREEN_TEXT = "#46614F"
CORAL_TEXT = "#B23A44"
YELLOW_TEXT = "#86650D"
PINK_TEXT = "#9C3F78"
LAV_TEXT = "#6A45B0"
TURQ_TEXT = "#1F7C76"
GREEN_TINT = "#E5EEE7"
CORAL_TINT = "#FDE9EA"
YELLOW_TINT = "#FCF4DC"
PINK_TINT = "#FAE9F4"
LAV_TINT = "#F1EAFC"
TURQ_TINT = "#E2F5F3"
SOFT = "#F5F7F4"          # quiet fills inside white cards
LINE_SOFT = "#EEF1ED"
DARK_LINE = "#2A2E37"
DARK_TEXT = "#E7E9EE"
DARK_MUTED = "#9AA1AD"

# ---------------------------------------------------------------- entity colours (graph, evidence trail, legends)
ENTITY = {  # kind -> (colour, plotly symbol, label)
    "document": (PINK, "square", "Document"),
    "rule": (TURQUOISE, "octagon", "Brand rule"),
    "case": (YELLOW, "diamond", "Test case"),
    "finding": (CORAL, "circle", "Finding"),
    "decision": (LAVENDER, "diamond-wide", "Decision"),
    "product": (MINT, "hexagon", "Product / campaign"),
}
OUTCOME = {  # RuleProbe outcome -> (fill, text, dark-fill)
    "Likely compliant": (GREEN_TINT, GREEN_TEXT, "#7FD3A0"),
    "Potential violation": (CORAL_TINT, CORAL_TEXT, CORAL),
    "Uncertain": (YELLOW_TINT, YELLOW_TEXT, YELLOW),
    "Needs human review": (PINK_TINT, PINK_TEXT, PINK),
}

# ---------------------------------------------------------------- names used across screens (mapped to the new palette)
PAPER = SOFT
INK = TEXT
INK_2 = "#3A403B"
TERRACOTTA = FOREST
TERRA_TEXT = FOREST
TERRA_BUTTON = FOREST
TERRA_TINT = SAGE_LIGHT
OLIVE = GREEN
OLIVE_TEXT = GREEN_TEXT
OLIVE_TINT = GREEN_TINT
SAND = MINT
SAND_TINT = SOFT
AMBER_TOKEN = YELLOW
AMBER_TEXT = YELLOW_TEXT
AMBER_TINT = YELLOW_TINT
MUTED_RED = CORAL
RED_TEXT = CORAL_TEXT
RED_TINT = CORAL_TINT
SECONDARY = TEXT_2
LINE = BORDER
SURFACE = WHITE
AMBER = YELLOW_TEXT
RED = CORAL

TONES = {  # badge background, foreground — all ≥ 4.5:1
    "neutral": ("#EEF1ED", "#4B524C"), "sage": (GREEN_TINT, GREEN_TEXT), "olive": (GREEN_TINT, GREEN_TEXT),
    "green": (GREEN_TINT, GREEN_TEXT), "amber": (YELLOW_TINT, YELLOW_TEXT), "yellow": (YELLOW_TINT, YELLOW_TEXT),
    "red": (CORAL_TINT, CORAL_TEXT), "coral": (CORAL_TINT, CORAL_TEXT), "pink": (PINK_TINT, PINK_TEXT),
    "lavender": (LAV_TINT, LAV_TEXT), "turquoise": (TURQ_TINT, TURQ_TEXT), "forest": (FOREST, WHITE),
    "ink": (FOREST, WHITE), "terracotta": (SAGE_LIGHT, FOREST), "indigo": (SAGE_LIGHT, FOREST),
}
ROOT_COLORS = {"Creator error": FOREST, "Guideline defect": YELLOW, "Source conflict": CORAL, "Knowledge gap": LAVENDER,
               "Unresolved / other": MINT}
CHART_SEQ = [GREEN, FOREST, MINT, YELLOW, CORAL, LAVENDER, TURQUOISE, PINK]

# Chart-strength steps of the brand hues. The pastel tokens are for tints and chips; data marks use these deeper steps,
# validated together (lightness band, chroma floor, colour-blind and normal-vision separation on the white card).
# Neutral grey is reserved for "other / unresolved".
CH_GREEN, CH_AMBER, CH_CORAL, CH_PURPLE, CH_PINK, CH_NEUTRAL = "#2F8A5F", "#D69A1F", "#E0626A", "#8C63D6", "#C2559F", "#98A29B"
ROOT_CHART = {"Creator error": CH_GREEN, "Guideline defect": CH_AMBER, "Source conflict": CH_CORAL, "Knowledge gap": CH_PURPLE,
              "Unresolved / other": CH_NEUTRAL}
CLASS_CHART = {"Violation": CH_PURPLE, "Contradicted": CH_CORAL, "Unsupported": CH_AMBER, "Unverifiable": CH_PINK,
               "Needs review": CH_NEUTRAL}
DECISION_CHART = {"Approved": CH_GREEN, "Changes requested": CH_AMBER, "Escalated": CH_PURPLE, "Rejected": CH_CORAL}
SEVERITY_CHART = {"high": CH_CORAL, "medium": CH_AMBER, "low": CH_NEUTRAL, "info": CH_NEUTRAL}
SEVERITY = {"high": CORAL, "medium": YELLOW, "low": MINT, "info": GREEN}

DISPLAY = "Manrope, Inter, 'Helvetica Neue', Arial, sans-serif"
BODY = "Inter, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, Menlo, monospace"
SIDEBAR_W = 244

FONTS = ("@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=Inter:wght@400;500;600;700"
         "&family=JetBrains+Mono:wght@400;600&display=swap');")

CSS = f"""
<style>
{FONTS}
/* ================= frame: sage around a large white rounded workspace ================= */
.stApp, [data-testid="stAppViewContainer"] {{ background: {SAGE}; }}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stMain"] {{ background: {SAGE}; }}
[data-testid="stMainBlockContainer"], .block-container {{
    background: {WHITE}; border-radius: 30px; margin: 14px 16px 16px 6px; padding: 18px 34px 64px !important;
    max-width: none; min-height: calc(100vh - 30px); box-shadow: 0 10px 40px rgba(16,28,22,.18);
    width: auto !important; align-self: stretch !important;   /* fill the space beside the sidebar, margins included */
    flex: 0 0 auto !important; height: auto !important; }}  /* grow with the content, never shrink to the viewport */
/* sidebar hidden: the workspace takes the whole width; the reopen button sits in the panel's own left gutter */
.stApp:has([data-testid="stExpandSidebarButton"]) [data-testid="stMainBlockContainer"] {{ margin-left: 16px; padding-left: 68px !important; }}
[data-testid="stExpandSidebarButton"] {{ position: fixed !important; left: 30px !important; top: 66px !important; z-index: 1000;
    width: 34px !important; height: 34px !important; border-radius: 11px !important; background: {FOREST} !important; color: #fff !important; }}
[data-testid="stExpandSidebarButton"] *, [data-testid="stExpandSidebarButton"] svg {{ color: #fff !important; fill: #fff !important; }}
h1, h2, h3, h4, h5, [data-testid="stHeading"] h3, [data-testid="stHeading"] h4,
[data-testid="stMarkdownContainer"] h3, [data-testid="stMarkdownContainer"] h4, [data-testid="stMarkdownContainer"] h5 {{
    font-family: {DISPLAY} !important; font-weight: 700 !important; letter-spacing: -0.015em; color: {TEXT}; }}
h4 {{ font-size: 1.02rem !important; }} h5 {{ font-size: .9rem !important; }}
::selection {{ background: {MINT}; }}
:focus-visible {{ outline: 2px solid {GREEN} !important; outline-offset: 2px; }}
code {{ font-family: {MONO}; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: {MUTED} !important; }}

/* buttons */
button[kind="primary"], button[data-testid="stBaseButton-primary"], button[kind="primaryFormSubmit"],
button[data-testid="stBaseButton-primaryFormSubmit"] {{
    background: {FOREST} !important; border-color: {FOREST} !important; color: #fff !important; border-radius: 12px !important;
    font-weight: 600; transition: background .15s ease, transform .15s ease; }}
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover, button[kind="primaryFormSubmit"]:hover {{
    background: #1A2A23 !important; border-color: #1A2A23 !important; }}
button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-secondaryFormSubmit"] {{
    border-radius: 12px !important; border-color: {BORDER} !important; background: {WHITE}; color: {TEXT}; font-weight: 500;
    transition: border-color .15s ease, background .15s ease; }}
button[data-testid="stBaseButton-secondary"]:hover {{ border-color: {GREEN} !important; color: {FOREST} !important; background: {SOFT}; }}
button[data-testid="stBaseButton-tertiary"] p {{ color: {GREEN_TEXT}; font-weight: 600; }}
button[data-testid="stBaseButton-tertiary"]:hover p {{ color: {FOREST}; }}
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input, [data-testid="stDateInput"] input {{ background: {WHITE}; }}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div, [data-testid="stTextInputRootElement"],
[data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"], [data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stTextArea"] textarea {{ border-radius: 12px !important; }}
[data-testid="stBaseButton-pills"] {{ border-radius: 999px !important; }}
[data-testid="stBaseButton-pillsActive"] {{ background: {GREEN_TINT} !important; border-color: {GREEN} !important; border-radius: 999px !important; }}
[data-testid="stBaseButton-pillsActive"] p {{ color: {FOREST} !important; font-weight: 600; }}

/* ================= sidebar: full-height navigation on the sage frame ================= */
[data-testid="stSidebar"] {{ background: {SAGE} !important; border-right: 0; }}
/* a fixed width only while the sidebar is open, so collapsing still hands the whole width back to the workspace */
.stApp:not(:has([data-testid="stExpandSidebarButton"])) [data-testid="stSidebar"] {{ width: 268px !important; min-width: 268px !important;
    max-width: 268px !important; }}
@media (max-width: 1180px) {{
  .stApp:not(:has([data-testid="stExpandSidebarButton"])) [data-testid="stSidebar"] {{ width: 236px !important; min-width: 236px !important;
      max-width: 236px !important; }} }}
@media (max-height: 860px) {{
  [data-testid="stSidebar"] [data-testid="stPageLink"] a {{ min-height: 40px; padding: 7px 12px; }}
  .bc-navlabel {{ padding: 10px 0 4px 12px; }}
  .bc-side-me {{ padding: 9px 12px; }} .bc-side-me .bc-avatar {{ width: 34px; height: 34px; }}
  .bc-ai {{ padding: 11px 14px; gap: 7px; }} }}
[data-testid="stSidebar"] > div {{ background: {SAGE}; }}
[data-testid="stSidebarHeader"] {{ height: 2.6rem; min-height: 0; padding: .5rem .8rem 0; }}
[data-testid="stSidebarHeader"] button, [data-testid="stSidebarCollapseButton"] button {{ color: #E8EEE9 !important; }}
[data-testid="stSidebarCollapsedControl"] button {{ background: {FOREST} !important; color: #fff !important; border-radius: 10px !important; }}
/* the navigation fills the panel top to bottom; the person and engine cards sit at its foot */
[data-testid="stSidebarContent"] {{ display: flex; flex-direction: column; padding-left: 6px !important; padding-right: 6px !important; }}
[data-testid="stSidebarUserContent"] {{ flex: 1 0 auto; display: flex; flex-direction: column; padding: 0 .8rem 1.1rem; }}
[data-testid="stSidebarUserContent"] > div {{ flex: 1 0 auto; display: flex; flex-direction: column; }}
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {{ flex: 1 0 auto; gap: .3rem; }}
[data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-side-foot) {{ margin-top: auto; padding-top: 18px; }}
.bc-navlabel {{ display: block; font-size: .72rem; color: rgba(255,255,255,.6); font-weight: 700; letter-spacing: .1em;
               text-transform: uppercase; padding: 16px 0 6px 14px; line-height: 1.4; }}
[data-testid="stSidebar"] [data-testid="stPageLink"], [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{ height: auto !important; }}
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {{ margin: 0 !important; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {{ display: flex !important; align-items: center; gap: 12px; min-height: 46px;
    box-sizing: border-box; border-radius: 14px; padding: 10px 14px; margin: 0; transition: background .15s ease; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p, [data-testid="stSidebar"] [data-testid="stPageLink"] a span {{
    font-size: 1rem; white-space: normal; line-height: 1.3; color: rgba(255,255,255,.86) !important; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a [data-testid="stIconMaterial"] {{ font-size: 1.3rem !important; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{ background: rgba(255,255,255,.09); }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {{ background: rgba(255,255,255,.17);
    box-shadow: inset 3px 0 0 {MINT}; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] p,
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] span {{ color: #fff !important; font-weight: 700; }}
.st-key-side-foot {{ gap: 10px !important; }}
.bc-side-me {{ display: flex; gap: 12px; align-items: center; background: rgba(255,255,255,.08); border-radius: 18px; padding: 12px 14px; }}
.bc-side-me .bc-avatar {{ width: 40px; height: 40px; background: {MINT}; color: {FOREST}; font-size: .9rem; }}
.bc-side-me .n {{ color: #fff; font-weight: 700; font-size: .98rem; line-height: 1.2; }}
.bc-side-me .r {{ color: rgba(255,255,255,.68); font-size: .78rem; line-height: 1.35; }}
.bc-ai {{ margin-top: 6px; background: rgba(255,255,255,.08); border-radius: 18px; padding: 14px 16px; display: flex; flex-direction: column; gap: 9px; }}
.bc-side-t {{ font-size: .72rem; color: rgba(255,255,255,.62); font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }}
.bc-ai-row {{ display: flex; gap: 10px; align-items: flex-start; }}
.bc-ai-row i {{ width: 9px; height: 9px; border-radius: 50%; flex: none; margin-top: 6px; box-shadow: 0 0 0 3px rgba(255,255,255,.12); }}
.bc-ai-row b {{ display: block; color: #fff; font-size: .92rem; font-weight: 700; line-height: 1.35; }}
.bc-ai-row span {{ display: block; color: rgba(255,255,255,.68); font-size: .8rem; line-height: 1.4; margin-top: 2px; word-break: break-word; }}
.bc-ai-row.err b {{ font-size: .82rem; }}
.bc-demo {{ align-self: flex-start; display: inline-block; background: rgba(240,207,114,.2); color: #F6E3A8; border-radius: 8px;
           padding: 4px 10px; font-size: .76rem; font-weight: 600; }}
.bc-side-note {{ font-size: .74rem; color: rgba(255,255,255,.66); line-height: 1.45; }}

/* ================= top bar ================= */
.st-key-topbar {{ border-bottom: 1px solid {BORDER}; padding: 2px 0 14px; margin-bottom: 22px; gap: 14px; align-items: center; }}
.bc-brand {{ display: flex; gap: 10px; align-items: center; white-space: nowrap; }}
.bc-brand svg {{ flex: none; width: 34px; height: 34px; }}
.bc-brand .name {{ font-family: {DISPLAY}; font-weight: 800; font-size: clamp(1rem, 1.5vw, 1.22rem); color: {TEXT}; line-height: 1; letter-spacing: -0.02em; }}
.bc-brand .desc {{ font-size: .62rem; letter-spacing: .08em; color: {MUTED}; font-weight: 600; margin-top: 3px; text-transform: uppercase; }}
.st-key-topbar [data-testid="stTextInput"] input {{ background: {SOFT}; border-radius: 12px; }}
.st-key-topbar [data-baseweb="input"] {{ background: {SOFT}; border-color: transparent !important; border-radius: 12px !important; }}
.st-key-topbar [data-testid="stSelectbox"] [role="group"] {{ background: {SOFT}; border-color: transparent !important; border-radius: 12px; }}
.bc-avatar {{ width: 34px; height: 34px; border-radius: 50%; background: {FOREST}; color: #fff; display: grid; place-items: center;
             font-weight: 700; font-size: .8rem; flex: none; font-family: {DISPLAY}; }}
.bc-profile {{ display: flex; gap: 10px; align-items: center; }}
.bc-profile .n {{ font-weight: 600; font-size: .88rem; color: {TEXT}; line-height: 1.2; }}
.bc-profile .r {{ font-size: .74rem; color: {MUTED}; }}

/* ================= page header ================= */
.bc-head {{ margin: 0 0 20px; }}
.bc-eyebrow {{ font-size: .74rem; color: {GREEN_TEXT}; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 6px; }}
.bc-title {{ font-family: {DISPLAY}; font-weight: 800; font-size: clamp(1.7rem, 2.6vw, 2.25rem); line-height: 1.12; color: {TEXT};
            letter-spacing: -0.025em; margin: 0 0 6px; }}
.bc-sub {{ color: {MUTED}; font-size: .98rem; line-height: 1.5; max-width: 70ch; }}
.bc-crumbs {{ display: none; }}

/* ================= cards ================= */
[class*="st-key-card-"], .st-key-chain, .st-key-library, .st-key-knowledge, .st-key-detail {{
    background: {WHITE}; border-radius: 24px !important; border-color: {BORDER} !important;
    box-shadow: 0 1px 2px rgba(16,28,22,.04), 0 6px 20px rgba(16,28,22,.04); transition: box-shadow .2s ease; }}
[class*="st-key-tint-"] {{ background: {SAGE_LIGHT}; border-radius: 24px !important; border-color: transparent !important; }}
[class*="st-key-forest-"] {{ background: {FOREST}; border-radius: 24px !important; border-color: transparent !important; }}
[class*="st-key-forest-"] p, [class*="st-key-forest-"] span, [class*="st-key-forest-"] h4, [class*="st-key-forest-"] div {{ color: #EEF3EF; }}
[class*="st-key-forest-"] button[data-testid="stBaseButton-tertiary"] p {{ color: {MINT} !important; }}
.bc-card {{ background: {WHITE}; border: 1px solid {BORDER}; border-radius: 24px; padding: 16px 18px; }}
.bc-card-title {{ font-family: {DISPLAY}; font-weight: 700; font-size: 1.02rem; color: {TEXT}; display: flex; align-items: baseline;
                 justify-content: space-between; gap: 2px 8px; margin-bottom: 4px; flex-wrap: wrap; }}
.bc-card-title small {{ font-family: {BODY}; font-weight: 500; font-size: .76rem; color: {MUTED}; }}

/* metric cards */
.bc-metric {{ background: {WHITE}; border: 1px solid {BORDER}; border-radius: 24px; padding: 16px 18px 12px; height: 100%;
             box-shadow: 0 1px 2px rgba(16,28,22,.04), 0 6px 20px rgba(16,28,22,.04); position: relative; overflow: hidden; }}
.bc-metric .top {{ display: flex; align-items: center; justify-content: space-between; }}
.bc-metric .l {{ font-size: .84rem; color: {MUTED}; font-weight: 600; display: flex; align-items: center; gap: 8px; }}
.bc-metric .ic {{ width: 34px; height: 34px; border-radius: 11px; display: grid; place-items: center; background: {SAGE_LIGHT}; flex: none; }}
.bc-metric .ic svg {{ width: 18px; height: 18px; }}
.bc-metric .v {{ font-family: {DISPLAY}; font-weight: 800; font-size: 2.35rem; line-height: 1.1; color: {TEXT}; margin: 10px 0 2px;
                letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }}
.bc-metric .n {{ font-size: .78rem; color: {MUTED}; line-height: 1.35; min-height: 2.7em; }}
.bc-metric.txt .v {{ font-size: 1.5rem; padding: 6px 0 4px; }}
.bc-metric .dot {{ width: 8px; height: 8px; border-radius: 50%; background: {MINT}; }}
.bc-metric.alert .dot {{ background: {CORAL}; }} .bc-metric.warn .dot {{ background: {YELLOW}; }}
.bc-metric.ok .dot {{ background: {GREEN}; }} .bc-metric.accent .dot {{ background: {FOREST}; }}
.bc-metric.forest {{ background: {FOREST}; border-color: {FOREST}; }}
.bc-metric.forest .l, .bc-metric.forest .n {{ color: rgba(255,255,255,.72); }} .bc-metric.forest .v {{ color: #fff; }}
.bc-metric.forest .ic {{ background: rgba(255,255,255,.12); }}

/* metric rows: every card in a row has the same height; a card's link sits inside the card, at its foot */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .bc-metric),
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-ml-"]) {{
    align-items: stretch !important; }}
[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .bc-metric),
[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-ml-"]) {{
    display: flex !important; flex-direction: column; }}
[data-testid="stColumn"] > [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .bc-metric),
[data-testid="stColumn"] > [data-testid="stVerticalBlock"]:has(> [data-testid="stLayoutWrapper"] > [class*="st-key-ml-"]),
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(> [class*="st-key-ml-"]),
[class*="st-key-ml-"] {{ flex: 1 1 auto; }}
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(.bc-metric),
[data-testid="stElementContainer"]:has(.bc-metric) [data-testid="stMarkdown"],
[data-testid="stElementContainer"]:has(.bc-metric) [data-testid="stMarkdown"] > div,
[data-testid="stElementContainer"]:has(.bc-metric) [data-testid="stMarkdownContainer"] {{
    flex: 1 1 auto; display: flex !important; flex-direction: column; }}
.bc-metric {{ flex: 1 1 auto; }}
[data-testid="stElementContainer"]:has(.bc-metric) [data-testid="stMarkdownContainer"] {{ margin: 0 !important; }}
[class*="st-key-ml-"] {{ background: {WHITE}; border: 1px solid {BORDER}; border-radius: 24px; gap: 0 !important; padding-bottom: 6px;
    box-shadow: 0 1px 2px rgba(16,28,22,.04), 0 6px 20px rgba(16,28,22,.04); overflow: hidden; }}
[class*="st-key-ml-"]:has(.bc-metric.forest) {{ background: {FOREST}; border-color: {FOREST}; }}
[class*="st-key-ml-"] .bc-metric {{ border: none; box-shadow: none; background: transparent; border-radius: 0; padding-bottom: 4px; }}
[class*="st-key-ml-"] > [data-testid="stElementContainer"]:has(.bc-metric) {{ flex: 1 1 auto; display: flex !important; flex-direction: column; }}
[class*="st-key-ml-"] [data-testid="stElementContainer"]:has(button) {{ padding: 0 18px; flex: none; }}
[class*="st-key-ml-"] button {{ justify-content: flex-start !important; text-align: left; }}
[class*="st-key-ml-"] button p {{ text-align: left; }}
[class*="st-key-ml-"]:has(.bc-metric.forest) button p {{ color: {MINT} !important; }}

[data-testid="stButtonGroup"] > div {{ flex-wrap: wrap !important; overflow: visible !important; row-gap: 6px; }}

/* chart helpers: headline figures above a chart, ranked lists with proportional bars */
.bc-cstat {{ display: flex; flex-wrap: wrap; gap: 4px 18px; margin: 2px 0 6px; font-size: .78rem; color: {MUTED}; }}
.bc-cstat b {{ font-family: {DISPLAY}; font-size: 1.05rem; font-weight: 800; color: {TEXT}; margin-right: 5px;
              font-variant-numeric: tabular-nums; }}
.bc-rank {{ display: flex; flex-direction: column; gap: 9px; margin: 8px 0 6px; }}
.bc-rank .r {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(56px, 26%) minmax(24px, auto); align-items: center; gap: 10px; }}
.bc-rank .l {{ font-size: .86rem; color: {TEXT}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.bc-rank .l .bc-code {{ margin-right: 6px; }}
.bc-rank .b {{ height: 8px; background: {LINE_SOFT}; border-radius: 99px; overflow: hidden; }}
.bc-rank .b i {{ display: block; height: 100%; border-radius: 99px; }}
.bc-rank .n {{ font-size: .82rem; font-weight: 700; color: {TEXT}; text-align: right; font-variant-numeric: tabular-nums;
              white-space: nowrap; }}

.bc-kg-h {{ font-size: .7rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: {DARK_MUTED};
            margin: 16px 0 2px; }}
.bc-rank.dk .l, .bc-rank.dk .n {{ color: {DARK_TEXT}; }}
.bc-rank.dk .b {{ background: #262A33; }}


/* ================= rounded everywhere: charts, tables, alerts, uploads, popovers ================= */
[data-testid="stPlotlyChart"] {{ border-radius: 18px; overflow: hidden; }}
[data-testid="stDataFrame"], [data-testid="stTable"], .stDataFrame {{ border-radius: 16px; overflow: hidden; }}
[data-testid="stAlert"], [data-testid="stAlertContainer"], [data-testid="stAlert"] > div {{ border-radius: 16px !important; }}
[data-testid="stFileUploaderDropzone"] {{ border-radius: 18px !important; }}
[data-testid="stPopoverBody"], [data-baseweb="popover"] > div {{ border-radius: 18px !important; }}
[data-testid="stPopoverButton"], [data-testid="stBaseButton-headerNoPadding"] {{ border-radius: 12px !important; }}

/* ================= balanced rows: cards side by side share one height ================= */
[class*="st-key-pair-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {{ align-items: stretch !important; }}
[class*="st-key-pair-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    display: flex !important; flex-direction: column; }}
[class*="st-key-pair-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
    flex: 1 1 auto; }}
[class*="st-key-pair-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > [data-testid="stVerticalBlock"]
    > [data-testid="stLayoutWrapper"]:last-child {{ flex: 1 1 auto; display: flex; flex-direction: column; }}
[class*="st-key-pair-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > [data-testid="stVerticalBlock"]
    > [data-testid="stLayoutWrapper"]:last-child > [class*="st-key-card-"] {{ flex: 1 1 auto; }}

[class*="st-key-pair-"] [class*="st-key-card-"] > [data-testid="stElementContainer"]:last-child:has(button),
[class*="st-key-pair-"] [class*="st-key-card-"] > [data-testid="stLayoutWrapper"]:last-child:has(button) {{ margin-top: auto; }}

/* ================= split workspaces: side panels follow the reader down the page ================= */
[class*="st-key-wrap-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {{ align-items: stretch !important; }}
[class*="st-key-wrap-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
    height: 100%; }}
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-stick-"]) {{ position: sticky; top: 14px; align-self: stretch; z-index: 3; }}
[class*="st-key-stick-"] {{ max-height: calc(100vh - 28px); overflow-y: auto; overflow-x: hidden; scrollbar-width: thin;
    border-radius: 24px; padding-bottom: 2px; }}
[class*="st-key-stick-"] > * {{ flex-shrink: 0; }}

/* badges, text helpers */
.bc-badge {{ display: inline-block; font-size: .72rem; font-weight: 600; border-radius: 999px; padding: 1px 9px;
            margin: 0 4px 3px 0; white-space: nowrap; line-height: 1.65; }}
.bc-muted {{ color: {MUTED}; font-size: .86rem; }}
.bc-mono {{ font-family: {MONO}; font-size: .75rem; letter-spacing: -0.01em; color: {MUTED}; }}
.bc-code {{ font-family: {MONO}; font-size: .76rem; font-weight: 600; color: {TURQ_TEXT}; background: {TURQ_TINT}; border-radius: 6px; padding: 1px 6px; }}
.bc-prov {{ margin: 10px 0 4px; font-size: .84rem; color: {MUTED}; }}
.bc-illustrative {{ background: {YELLOW_TINT}; color: {YELLOW_TEXT}; border-radius: 12px; padding: 8px 14px; font-size: .82rem; }}
.bc-empty {{ border: 1.5px dashed {MINT}; border-radius: 24px; padding: 30px; text-align: center; color: {MUTED}; background: {SOFT}; }}
.bc-empty b {{ color: {TEXT}; display: block; font-family: {DISPLAY}; font-weight: 700; font-size: 1.2rem; margin-bottom: 4px; }}

/* ================= evidence trail (improvement 2) ================= */
.bc-trail {{ display: flex; flex-wrap: wrap; align-items: stretch; row-gap: 6px; margin: 10px 0 4px; }}
.bc-trail .node {{ position: relative; background: {WHITE}; border: 1px solid {BORDER}; border-radius: 12px; padding: 6px 10px 6px 24px;
                  min-width: 0; max-width: 100%; }}
.bc-trail .node::before {{ content: ""; position: absolute; left: 9px; top: 11px; width: 8px; height: 8px; border-radius: 3px; background: {MINT}; }}
.bc-trail .node.k-content::before {{ background: {GREEN}; border-radius: 50%; }}
.bc-trail .node.k-rule::before {{ background: {TURQUOISE}; }}
.bc-trail .node.k-source::before, .bc-trail .node.k-document::before {{ background: {PINK}; border-radius: 1px; }}
.bc-trail .node.k-evidence::before, .bc-trail .node.k-passage::before {{ background: {PINK}; border-radius: 50%; }}
.bc-trail .node.k-test::before {{ background: {YELLOW}; transform: rotate(45deg); }}
.bc-trail .node.k-finding::before {{ background: {CORAL}; border-radius: 50%; }}
.bc-trail .node.decision::before, .bc-trail .node.k-decision::before {{ background: {LAVENDER}; transform: rotate(45deg); }}
.bc-trail .node .k {{ font-size: .64rem; color: {MUTED}; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; }}
.bc-trail .node .v {{ font-family: {MONO}; font-size: .72rem; color: {TEXT}; line-height: 1.4; word-break: break-word; }}
.bc-trail .node.missing {{ border-style: dashed; }}
.bc-trail .node.missing .v {{ color: {CORAL_TEXT}; font-family: {BODY}; font-style: italic; }}
.bc-trail .link {{ align-self: center; width: 14px; border-top: 1.5px solid {MINT}; }}
.bc-evidence, .bc-quote {{ border-left: 3px solid {PINK}; padding: 8px 12px; margin: 8px 0; font-size: .9rem; color: {INK_2};
               line-height: 1.55; background: {PINK_TINT}; border-radius: 0 12px 12px 0; }}
.bc-evidence .src, .bc-quote .src {{ font-family: {MONO}; font-size: .7rem; color: {MUTED}; margin-top: 4px; }}

/* ================= findings ================= */
.bc-finding {{ border-left: 3px solid {MINT}; padding: 2px 0 2px 14px; }}
.bc-finding.high {{ border-left-color: {CORAL}; }} .bc-finding.medium {{ border-left-color: {YELLOW}; }}
.bc-finding.low {{ border-left-color: {MINT}; }} .bc-finding.info {{ border-left-color: {GREEN}; }}
.bc-finding .phrase {{ font-family: {DISPLAY}; font-weight: 700; font-size: 1.08rem; line-height: 1.35; color: {TEXT}; margin: 4px 0 6px; }}
.bc-finding .tag {{ font-family: {MONO}; font-size: .72rem; color: {MUTED}; }}
.bc-precedent {{ background: {LAV_TINT}; border-radius: 12px; padding: 10px 14px; font-size: .86rem; color: {INK_2}; margin: 8px 0;
                border-left: 3px solid {LAVENDER}; }}
.bc-precedent b {{ color: {LAV_TEXT}; }}
.bc-correction {{ background: {GREEN_TINT}; border-radius: 14px; padding: 10px 14px; margin: 8px 0 4px; }}
.bc-correction .k {{ font-size: .68rem; font-weight: 700; color: {GREEN_TEXT}; letter-spacing: .06em; text-transform: uppercase; }}

/* ================= audited text ================= */
.bc-text {{ background: {WHITE}; border: 1px solid {BORDER}; border-radius: 18px; padding: 18px 22px; font-size: 1.06rem;
           line-height: 2.05; color: {TEXT}; }}
.bc-text mark {{ background: transparent; color: inherit; padding: 1px 2px; border-radius: 4px; text-decoration-line: underline;
                text-decoration-thickness: 2px; text-underline-offset: 5px; transition: opacity .2s ease; }}
.bc-text mark.m-high {{ text-decoration-color: {CORAL}; background: {CORAL_TINT}; }}
.bc-text mark.m-medium {{ text-decoration-color: {YELLOW}; background: {YELLOW_TINT}; }}
.bc-text mark.m-low {{ text-decoration-color: {MINT}; text-decoration-style: dotted; }}
.bc-text.focus mark {{ opacity: .35; }}
.bc-text.focus mark.on {{ opacity: 1; outline: 2px solid {FOREST}; outline-offset: 2px; }}
.bc-text sup.flag {{ display: inline-block; min-width: 17px; height: 17px; line-height: 17px; text-align: center; border-radius: 5px;
                    font-size: .64rem; font-weight: 700; color: #fff; margin-left: 2px; vertical-align: super; font-family: {MONO}; }}
.bc-text sup.f-high {{ background: {CORAL_TEXT}; }} .bc-text sup.f-medium {{ background: {YELLOW_TEXT}; }} .bc-text sup.f-low {{ background: {MUTED}; }}
.bc-diff ins {{ background: {GREEN_TINT}; color: {GREEN_TEXT}; text-decoration: none; border-radius: 4px; padding: 0 3px; }}
.bc-diff del {{ color: {CORAL_TEXT}; text-decoration-thickness: 1.5px; padding: 0 2px; }}

/* ================= timeline ================= */
.bc-tl {{ position: relative; margin: 4px 0 0 6px; padding-left: 18px; border-left: 1.5px solid {BORDER}; }}
.bc-tl .ev {{ position: relative; padding: 0 0 14px; }}
.bc-tl .ev::before {{ content: ""; position: absolute; left: -24px; top: 4px; width: 10px; height: 10px; border-radius: 50%;
                     background: {WHITE}; border: 2px solid {MINT}; }}
.bc-tl .ev.t-terracotta::before, .bc-tl .ev.t-forest::before {{ border-color: {FOREST}; }}
.bc-tl .ev.t-olive::before {{ border-color: {GREEN}; background: {GREEN}; }}
.bc-tl .ev.t-amber::before {{ border-color: {YELLOW}; background: {YELLOW}; }}
.bc-tl .ev.t-red::before {{ border-color: {CORAL}; background: {CORAL}; }}
.bc-tl .ev .w {{ font-family: {MONO}; font-size: .7rem; color: {MUTED}; }}
.bc-tl .ev .a {{ font-size: .88rem; color: {TEXT}; font-weight: 600; line-height: 1.35; }}
.bc-tl .ev .d {{ font-size: .82rem; color: {MUTED}; line-height: 1.45; }}

/* ================= document rows / cards ================= */
.bc-doc {{ display: flex; gap: 12px; align-items: flex-start; }}
.bc-doc .ic {{ width: 36px; height: 42px; border-radius: 9px; background: {PINK_TINT}; flex: none; font-family: {MONO}; font-size: .58rem;
              font-weight: 700; color: {PINK_TEXT}; display: grid; place-items: end center; padding-bottom: 5px; position: relative; }}
.bc-doc .ic::before {{ content: ""; position: absolute; top: 8px; left: 9px; width: 12px; height: 2px; background: {PINK};
                      box-shadow: 0 5px 0 {PINK}, 0 10px 0 {PINK}; border-radius: 2px; }}
.bc-doc .t {{ font-weight: 600; font-size: .92rem; color: {TEXT}; line-height: 1.3; }}
.bc-doc .m {{ font-family: {MONO}; font-size: .7rem; color: {MUTED}; margin-top: 3px; }}

/* ================= tables ================= */
.bc-table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: .88rem; background: {WHITE};
            border: 1px solid {BORDER}; border-radius: 14px; overflow: hidden; }}
.bc-table th {{ text-align: left; font-weight: 600; color: {MUTED}; font-size: .74rem; padding: 10px 12px; letter-spacing: .03em;
               border-bottom: 1px solid {BORDER}; background: {SOFT}; }}
.bc-table td {{ padding: 10px 12px; border-bottom: 1px solid {LINE_SOFT}; vertical-align: top; }}
.bc-table tr:last-child td {{ border-bottom: 0; }}
.bc-kv {{ table-layout: fixed; overflow-wrap: anywhere; }} .bc-kv td:first-child {{ width: 40%; }}
.bc-table tr.hl td {{ background: {YELLOW_TINT}; }}
.v-pass, .v-fail, .v-unclear, .v-review {{ display: inline-block; font-size: .72rem; font-weight: 600; padding: 1px 9px; border-radius: 999px; }}
.v-pass {{ background: {GREEN_TINT}; color: {GREEN_TEXT}; }} .v-fail {{ background: {CORAL_TINT}; color: {CORAL_TEXT}; }}
.v-unclear {{ background: {YELLOW_TINT}; color: {YELLOW_TEXT}; }} .v-review {{ background: {PINK_TINT}; color: {PINK_TEXT}; }}

/* ================= feeds / lists ================= */
.bc-row {{ display: flex; align-items: center; gap: 10px; padding: 9px 0; border-bottom: 1px solid {LINE_SOFT}; font-size: .88rem; }}
.bc-row:last-child {{ border-bottom: 0; }}
.bc-row .ic {{ width: 30px; height: 30px; border-radius: 10px; display: grid; place-items: center; flex: none; font-size: .8rem; font-weight: 700; }}
.bc-row .b {{ flex: 1; min-width: 0; }}
.bc-row .b .t {{ font-weight: 600; color: {TEXT}; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2;
                -webkit-box-orient: vertical; overflow: hidden; }}
.bc-row .b .s {{ font-size: .76rem; color: {MUTED}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.bc-row .w {{ font-family: {MONO}; font-size: .7rem; color: {MUTED}; white-space: nowrap; }}
.bc-feed {{ font-size: .88rem; padding: 9px 0; border-bottom: 1px solid {LINE_SOFT}; }}
.bc-feed:last-child {{ border-bottom: 0; }}

/* progress bars and stacked health bar */
.bc-bar {{ height: 10px; border-radius: 999px; background: {SOFT}; overflow: hidden; display: flex; }}
.bc-bar i {{ display: block; height: 100%; }}
.bc-legend {{ display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: .78rem; color: {MUTED}; margin-top: 8px; }}
.bc-legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
.bc-legend i {{ width: 9px; height: 9px; border-radius: 3px; display: inline-block; }}
.bc-big {{ font-family: {DISPLAY}; font-weight: 800; font-size: 2.6rem; letter-spacing: -0.03em; color: {TEXT}; line-height: 1; }}
.bc-big small {{ font-size: .9rem; color: {MUTED}; font-weight: 600; letter-spacing: 0; margin-left: 6px; }}

/* tabs */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 0; background: {SOFT}; padding: 4px; border-radius: 12px; width: fit-content; max-width: 100%; }}
.stTabs [data-baseweb="tab"] {{ padding: 6px 14px; font-weight: 600; border-radius: 9px; height: auto; }}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{ background: {WHITE}; box-shadow: 0 1px 3px rgba(16,28,22,.12); }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}
[data-testid="stExpander"] details {{ border-radius: 18px !important; border-color: {BORDER} !important; overflow: hidden; }}
[data-testid="stExpander"] summary {{ border-radius: 18px; }}
[data-testid="stPopoverBody"] {{ border-radius: 16px; }}

/* ================= source page, before/after, specimen ================= */
.bc-page {{ background: #FFFEFB; border: 1px solid {BORDER}; border-radius: 16px; padding: 14px 18px 10px;
           box-shadow: 0 2px 0 {SOFT}, 0 6px 18px rgba(16,28,22,.07); font-family: Georgia, 'Times New Roman', serif;
           font-size: .88rem; line-height: 1.55; color: {INK_2}; max-height: 300px; overflow-y: auto; }}
.bc-page .hd, .bc-page .ft {{ display: flex; justify-content: space-between; font-family: {MONO}; font-size: .68rem; color: {MUTED};
                             border-bottom: 1px solid {LINE_SOFT}; padding-bottom: 6px; margin-bottom: 8px; }}
.bc-page .ft {{ border-bottom: 0; border-top: 1px solid {LINE_SOFT}; padding: 6px 0 0; margin: 8px 0 0; }}
.bc-page p {{ margin: 0 0 6px; padding: 2px 6px; border-radius: 4px; }}
.bc-page p.cited {{ background: {PINK_TINT}; box-shadow: inset 3px 0 0 {PINK}; color: {TEXT}; font-weight: 600; }}
.bc-ba {{ display: grid; grid-template-columns: 1fr 34px 1fr; gap: 6px; align-items: stretch; margin: 2px 0 6px; }}
.bc-ba .side {{ border-radius: 16px; padding: 12px 14px; }}
.bc-ba .before {{ background: {CORAL_TINT}; }} .bc-ba .after {{ background: {GREEN_TINT}; }}
.bc-ba .k {{ font-family: {MONO}; font-size: .7rem; font-weight: 600; margin-bottom: 6px; }}
.bc-ba .before .k {{ color: {CORAL_TEXT}; }} .bc-ba .after .k {{ color: {GREEN_TEXT}; }}
.bc-ba .t {{ font-family: {DISPLAY}; font-weight: 600; font-size: 1.04rem; line-height: 1.45; color: {TEXT}; }}
.bc-ba .before .t {{ text-decoration: line-through; text-decoration-color: rgba(178,58,68,.35); }}
.bc-ba .arrow {{ display: flex; align-items: center; justify-content: center; font-size: 1.4rem; color: {GREEN}; }}
.bc-specimen {{ background: {WHITE}; border-radius: 16px; padding: 16px 18px; border: 1px solid {BORDER}; }}
.bc-specimen .code {{ font-family: {MONO}; font-size: .74rem; color: {MUTED}; }}
.bc-specimen .rule, .bc-specimen-rule {{ font-family: {DISPLAY}; font-weight: 700; font-size: 1.3rem; line-height: 1.3; color: {TEXT}; margin: 4px 0 8px; }}

/* governance: where to act */
.bc-fix .h {{ font-family: {DISPLAY}; font-weight: 800; font-size: 1.2rem; color: {TEXT}; line-height: 1.15; }}
.bc-fix .n {{ font-family: {DISPLAY}; font-weight: 800; font-size: 2.3rem; color: {TEXT}; line-height: 1.1; margin-top: 6px; }}
.bc-fix .n span {{ font-family: {BODY}; font-weight: 500; font-size: .78rem; color: {MUTED}; margin-left: 8px; }}
.bc-fix .bar {{ height: 8px; background: {SOFT}; border-radius: 999px; margin: 8px 0 10px; overflow: hidden; }}
.bc-fix .bar i {{ display: block; height: 100%; background: {MINT}; border-radius: 999px; }}
.bc-fix.top .bar i {{ background: {FOREST}; }}
.bc-fix .n em {{ font-style: normal; font-family: {MONO}; font-size: .64rem; color: #fff; background: {FOREST};
                border-radius: 24px; padding: 2px 8px; margin-left: 8px; vertical-align: middle; }}
.bc-fix .w {{ font-size: .86rem; color: {INK_2}; line-height: 1.45; min-height: 2.6em; }}

/* guided demo stepper */
.st-key-tour {{ background: {FOREST}; color: #fff; border-radius: 18px; padding: 12px 16px 10px; margin-bottom: 16px; gap: 6px; }}
.st-key-tour .tr-chips {{ display: flex; align-items: center; gap: 0; flex-wrap: wrap; row-gap: 6px; }}
.st-key-tour .tr-chip {{ display: flex; align-items: center; gap: 7px; font-size: .8rem; font-weight: 600; color: rgba(255,255,255,.6); }}
.st-key-tour .tr-chip b {{ width: 22px; height: 22px; border-radius: 50%; border: 1.5px solid rgba(255,255,255,.35); display: inline-flex;
                          align-items: center; justify-content: center; font-size: .72rem; font-family: {MONO}; }}
.st-key-tour .tr-chip.done {{ color: {MINT}; }} .st-key-tour .tr-chip.done b {{ background: {GREEN}; border-color: {GREEN}; color: #fff; }}
.st-key-tour .tr-chip.on {{ color: #fff; }} .st-key-tour .tr-chip.on b {{ background: {YELLOW}; border-color: {YELLOW}; color: {TEXT}; }}
.st-key-tour .tr-line {{ flex: 1; min-width: 14px; max-width: 60px; height: 1.5px; background: rgba(255,255,255,.22); margin: 0 8px; }}
.st-key-tour .tr-now {{ margin-top: 8px; font-size: .95rem; color: #fff; }}
.st-key-tour .tr-now .bc-muted {{ color: rgba(255,255,255,.66) !important; }}
.st-key-tour .tr-step {{ font-family: {MONO}; font-size: .72rem; color: {YELLOW}; letter-spacing: .04em; margin-right: 6px; }}
.st-key-tour .tr-tip {{ font-size: .86rem; color: rgba(255,255,255,.78); margin: 2px 0 10px; }}
.st-key-tour button[data-testid="stBaseButton-primary"] {{ background: {YELLOW} !important; border-color: {YELLOW} !important; }}
.st-key-tour button[data-testid="stBaseButton-primary"] p {{ color: {TEXT} !important; }}
.st-key-tour [data-testid="stBaseButton-tertiary"] p {{ color: rgba(255,255,255,.78) !important; }}
.st-key-tour-offer {{ background: {SAGE_LIGHT}; border-radius: 18px; padding: 12px 16px; margin: 0 0 16px; }}
.st-key-tour-offer .tr-offer {{ font-size: .92rem; color: {TEXT}; }}

/* RuleProbe step strip */
.bc-steps {{ display: flex; border: 1px solid {BORDER}; border-radius: 14px; overflow: hidden; background: {WHITE}; margin: 4px 0 6px; }}
.bc-step {{ flex: 1; padding: 9px 12px; border-right: 1px solid {LINE_SOFT}; min-width: 0; }}
.bc-step:last-child {{ border-right: 0; }}
.bc-step .t {{ font-size: .7rem; color: {MUTED}; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }}
.bc-step .d {{ font-size: .86rem; color: {TEXT}; font-weight: 600; margin-top: 2px; }}
.bc-step.on {{ background: {YELLOW_TINT}; }}

/* RuleProbe split view (light fallback; dark page overrides) */
.bc-split {{ display: flex; gap: 22px; align-items: center; background: {WHITE}; border: 1px solid {BORDER}; border-radius: 18px;
            padding: 16px 18px; margin: 6px 0 10px; flex-wrap: wrap; }}
.bc-split .sv-gauge {{ text-align: center; flex: none; }}
.bc-split .sv-gl {{ font-size: .82rem; font-weight: 600; color: {TEXT}; margin-top: -4px; }}
.bc-split .sv-gn {{ font-size: .76rem; color: {MUTED}; }}
.bc-split .sv-main {{ flex: 1; min-width: 300px; }}
.bc-split .sv-grid {{ display: flex; gap: 6px; overflow-x: auto; padding-bottom: 2px; }}
.bc-split .sv-legend {{ display: grid; grid-template-rows: 18px 38px 38px 30px; gap: 4px; font-size: .74rem; color: {MUTED};
                       font-weight: 600; flex: none; width: 54px; }}
.bc-split .sv-legend div {{ display: flex; align-items: center; }}
.bc-split .sv-col {{ display: grid; grid-template-rows: 18px 38px 38px 30px; gap: 4px; min-width: 46px; flex: 1; max-width: 86px;
                    border-radius: 12px; padding: 0 3px; border: 2px solid transparent; }}
.bc-split .sv-col.split {{ border-color: {YELLOW}; background: {YELLOW_TINT}; }}
.bc-split .sv-n {{ font-family: {MONO}; font-size: .72rem; color: {MUTED}; text-align: center; }}
.bc-split .sv-cell {{ border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; font-weight: 700; }}
.bc-split .sv-pass {{ background: {GREEN_TINT}; color: {GREEN_TEXT}; }}
.bc-split .sv-fail {{ background: {CORAL_TINT}; color: {CORAL_TEXT}; }}
.bc-split .sv-unclear {{ background: {YELLOW_TINT}; color: {YELLOW_TEXT}; }}
.bc-split .sv-d {{ font-size: .66rem; color: {MUTED}; text-align: center; line-height: 1.15; }}
.bc-split .sv-verdict {{ font-family: {DISPLAY}; font-weight: 700; font-size: 1.12rem; line-height: 1.35; color: {TEXT}; margin: 10px 0 4px; }}
.bc-gauge-arc {{ animation: bc-gauge .9s cubic-bezier(.3,0,.2,1) both; }}
@keyframes bc-gauge {{ from {{ stroke-dasharray: 0 400; }} }}

/* chips used as graph legends */
.bc-legend-chip {{ display: inline-flex; align-items: center; gap: 7px; font-size: .78rem; font-weight: 600; margin: 0 12px 6px 0; }}
.bc-legend-chip i {{ width: 11px; height: 11px; display: inline-block; }}

/* loading */
[data-testid="stSpinner"] i {{ border-top-color: {GREEN} !important; }}
@keyframes bc-fade {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
.bc-metric, [class*="st-key-card-"] {{ animation: bc-fade .35s ease both; }}
/* responsive: multi-panel workspaces stack (wrap-*) or pair up (pair-*) on narrower screens */
@media (max-width: 1180px) {{
  [class*="st-key-wrap-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"],
  [class*="st-key-pair-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; row-gap: 1rem; }}
  [class*="st-key-wrap-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
      flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important; }}
  [class*="st-key-pair-"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
      flex: 1 1 300px !important; min-width: 300px !important; }}
  .bc-brand .desc {{ display: none; }}
  [data-testid="stLayoutWrapper"]:has(> [class*="st-key-stick-"]) {{ position: static; }}
  [class*="st-key-stick-"] {{ max-height: none; overflow: visible; }}
  .st-key-topbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {{ flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }}
  .st-key-topbar .bc-brand .name {{ display: none; }}
  [data-testid="stMainBlockContainer"], .block-container {{ padding: 16px 22px 56px !important; }}
}}
@media (max-width: 900px) {{
  [data-testid="stMainBlockContainer"], .block-container {{ margin: 8px; border-radius: 24px; padding: 14px 16px 48px !important; }}
  .bc-trail .link {{ display: none; }} .bc-trail {{ gap: 6px; }} .bc-ba {{ grid-template-columns: 1fr; }}
  .bc-ba .arrow {{ transform: rotate(90deg); }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}

/* dark detail panel inside a light page (Decision Memory) */
[class*="st-key-darkpanel"] {{ background: {DARK_PANEL} !important; border-color: {DARK_PANEL} !important; border-radius: 24px !important; }}
[class*="st-key-darkpanel"] p, [class*="st-key-darkpanel"] span, [class*="st-key-darkpanel"] div, [class*="st-key-darkpanel"] label,
[class*="st-key-darkpanel"] li {{ color: {DARK_TEXT}; }}
[class*="st-key-darkpanel"] .bc-muted, [class*="st-key-darkpanel"] .bc-mono, [class*="st-key-darkpanel"] .bc-tl .ev .w,
[class*="st-key-darkpanel"] .bc-tl .ev .d, [class*="st-key-darkpanel"] .bc-trail .node .k {{ color: {DARK_MUTED} !important; }}
[class*="st-key-darkpanel"] .bc-specimen-rule, [class*="st-key-darkpanel"] .bc-trail .node .v,
[class*="st-key-darkpanel"] .bc-tl .ev .a, [class*="st-key-darkpanel"] strong {{ color: #fff !important; }}
[class*="st-key-darkpanel"] .bc-trail .node.missing .v {{ color: #F7A5AA !important; }}
[class*="st-key-darkpanel"] .bc-trail .node {{ background: #20232B; border-color: {DARK_LINE}; }}
[class*="st-key-darkpanel"] .bc-trail .link {{ border-top-color: #3A3F4B; }}
[class*="st-key-darkpanel"] .bc-quote, [class*="st-key-darkpanel"] .bc-evidence {{ background: rgba(231,155,208,.10); }}
[class*="st-key-darkpanel"] .bc-text {{ background: #20232B; border-color: {DARK_LINE}; color: {DARK_TEXT}; }}
[class*="st-key-darkpanel"] .bc-diff ins {{ background: rgba(127,211,160,.18); color: #9FE3BA; }}
[class*="st-key-darkpanel"] .bc-diff del {{ color: #F7A5AA; }}
[class*="st-key-darkpanel"] .bc-tl {{ border-left-color: {DARK_LINE}; }}
[class*="st-key-darkpanel"] .bc-tl .ev::before {{ background: {DARK_PANEL}; }}
[class*="st-key-darkpanel"] .bc-badge {{ filter: none; }}
[class*="st-key-darkpanel"] [data-testid="stExpander"] details {{ background: #20232B; border-color: {DARK_LINE} !important; }}
[class*="st-key-darkpanel"] [data-testid="stTextInputRootElement"] {{ background: #2A2E37 !important; border-color: #3A3F4B !important; }}
[class*="st-key-darkpanel"] input {{ color: {DARK_TEXT} !important; background: transparent !important; }}
[class*="st-key-darkpanel"] button[data-testid="stBaseButton-tertiary"] p {{ color: {TURQUOISE} !important; }}
[class*="st-key-darkpanel"] [data-testid="stAlert"] {{ background: rgba(240,207,114,.10); }}
</style>
"""

# ---------------------------------------------------------------- dark investigation workspace
DARK_CSS = f"""
<style>
[data-testid="stMainBlockContainer"], .block-container {{ background: {DARK_BG} !important; box-shadow: 0 10px 40px rgba(0,0,0,.35); }}
.block-container, .block-container p, .block-container li, .block-container label, .block-container span,
.block-container [data-testid="stMarkdownContainer"], .block-container [data-testid="stWidgetLabel"] p {{ color: {DARK_TEXT}; }}
.block-container h1, .block-container h2, .block-container h3, .block-container h4, .block-container h5,
.block-container [data-testid="stHeading"] * {{ color: #fff !important; }}
.block-container .bc-title {{ color: #fff; }} .block-container .bc-sub, .block-container .bc-muted,
.block-container .bc-mono, .block-container [data-testid="stCaptionContainer"] * {{ color: {DARK_MUTED} !important; }}
.block-container .bc-eyebrow {{ color: {TURQUOISE}; }}
.st-key-topbar {{ border-bottom-color: {DARK_LINE}; }}
.st-key-topbar .bc-brand .name, .st-key-topbar .bc-profile .n {{ color: #fff; }}
.st-key-topbar .bc-brand .desc, .st-key-topbar .bc-profile .r {{ color: {DARK_MUTED}; }}
.block-container [class*="st-key-card-"], .block-container .st-key-chain, .block-container .st-key-library,
.block-container .st-key-knowledge, .block-container .st-key-detail, .block-container [class*="st-key-panel-"] {{
    background: {DARK_PANEL} !important; border-color: {DARK_LINE} !important; box-shadow: none; }}
.block-container [class*="st-key-tint-"] {{ background: #20232B !important; }}
.block-container .bc-specimen-rule {{ color: #FFFFFF; }}
.block-container .st-key-panel-actionbar {{ border-radius: 24px !important; padding: 16px 18px !important; border: 1px solid {DARK_LINE}; margin-top: 8px; }}
.block-container [data-testid="stTextInput"] input, .block-container [data-testid="stTextArea"] textarea,
.block-container [data-baseweb="select"] > div, .block-container [data-baseweb="input"], .block-container [data-baseweb="textarea"],
.block-container [data-testid="stNumberInput"] input {{ background: #20232B !important; color: {DARK_TEXT} !important;
    border-color: {DARK_LINE} !important; }}
.block-container [data-testid="stSelectbox"] [role="group"], .block-container [data-testid="stMultiSelect"] [role="group"] {{
    background-color: #20232B !important; border-color: {DARK_LINE} !important; }}
.block-container [data-testid="stSelectbox"] input, .block-container [data-testid="stMultiSelect"] input {{ color: {DARK_TEXT} !important;
    background: transparent !important; }}
.block-container [data-testid="stSelectbox"] button svg, .block-container [data-testid="stMultiSelect"] button svg {{ color: {DARK_MUTED}; }}
.block-container [data-testid="stMultiSelect"] [data-tag] {{ background-color: #2F3440 !important; color: {DARK_TEXT} !important; }}
.block-container [data-baseweb="select"] svg {{ fill: {DARK_MUTED}; }}
.block-container [data-testid="stBaseButton-pills"] {{ background: #20232B !important; border-color: {DARK_LINE} !important; }}
.block-container [data-testid="stBaseButton-pills"] p {{ color: {DARK_MUTED} !important; }}
.block-container [data-testid="stBaseButton-pillsActive"] {{ background: rgba(86,201,193,.16) !important; border-color: {TURQUOISE} !important; }}
.block-container [data-testid="stBaseButton-pillsActive"] p {{ color: #fff !important; }}
.block-container [data-testid="stTextInputRootElement"], .block-container [data-testid="stTextAreaRootElement"] {{
    background: #20232B !important; border-color: {DARK_LINE} !important; }}
.block-container .bc-finding .phrase {{ color: #fff; }}
.block-container .bc-steps {{ background: {DARK_PANEL}; border-color: {DARK_LINE}; }}
.block-container .bc-step {{ border-right-color: {DARK_LINE}; }} .block-container .bc-step .d {{ color: {DARK_TEXT}; }}
.block-container .bc-step.on {{ background: rgba(240,207,114,.12); }} .block-container .bc-step.on .d {{ color: {YELLOW}; }}
.block-container [data-testid="stRadio"] [role="radiogroup"] label {{ padding: 3px 6px; border-radius: 8px; }}
.block-container [data-testid="stRadio"] [role="radiogroup"] label:hover {{ background: #20232B; }}
.block-container input::placeholder, .block-container textarea::placeholder {{ color: #6C7380 !important; }}
.block-container button[data-testid="stBaseButton-secondary"], .block-container button[data-testid="stBaseButton-secondaryFormSubmit"] {{
    background: #20232B !important; border-color: {DARK_LINE} !important; color: {DARK_TEXT} !important; }}
.block-container button[data-testid="stBaseButton-secondary"]:hover {{ border-color: {TURQUOISE} !important; color: #fff !important; }}
.block-container button[data-testid="stBaseButton-secondary"] p {{ color: {DARK_TEXT} !important; }}
.block-container button[data-testid="stBaseButton-primary"], .block-container button[data-testid="stBaseButton-primaryFormSubmit"] {{
    background: {TURQUOISE} !important; border-color: {TURQUOISE} !important; }}
.block-container button[data-testid="stBaseButton-primary"] p, .block-container button[data-testid="stBaseButton-primaryFormSubmit"] p {{
    color: #0B1F1D !important; font-weight: 700; }}
.block-container button[data-testid="stBaseButton-primary"]:hover {{ background: #6FD8D0 !important; }}
.block-container button[data-testid="stBaseButton-tertiary"] p {{ color: {TURQUOISE} !important; }}
.block-container button:disabled {{ opacity: .45; }}
.block-container .stTabs [data-baseweb="tab-list"] {{ background: #20232B; }}
.block-container .stTabs [data-baseweb="tab"] p {{ color: {DARK_MUTED} !important; }}
.block-container .stTabs [data-baseweb="tab"][aria-selected="true"] {{ background: #2C303A; box-shadow: none; }}
.block-container .stTabs [data-baseweb="tab"][aria-selected="true"] p {{ color: #fff !important; }}
.block-container [data-testid="stExpander"] details {{ background: {DARK_PANEL}; border-color: {DARK_LINE} !important; }}
.block-container [data-testid="stExpander"] summary {{ background: transparent !important; color: {DARK_TEXT} !important; }}
.block-container [data-testid="stExpander"] summary p, .block-container [data-testid="stExpander"] summary span,
.block-container [data-testid="stExpander"] summary svg {{ color: {DARK_TEXT} !important; fill: currentColor; }}
.block-container [data-testid="stExpander"] summary:hover p {{ color: {TURQUOISE} !important; }}
.block-container [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{ background: transparent !important; }}
.block-container [data-testid="stPlotlyChart"] {{ border-radius: 18px; }}
.block-container [data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p {{ color: {DARK_TEXT}; }}
.block-container [data-baseweb="radio"] div:first-child {{ border-color: #4A505C; }}
.block-container [data-baseweb="checkbox"] span {{ border-color: #4A505C; }}
.block-container [data-testid="stAlert"] {{ background: #20232B; }}
.block-container [data-testid="stPopover"] button {{ background: #20232B !important; border-color: {DARK_LINE} !important; }}
.block-container hr {{ border-color: {DARK_LINE}; }}
.block-container .bc-badge {{ filter: saturate(1.1); }}
.block-container .bc-code {{ background: rgba(86,201,193,.14); color: {TURQUOISE}; }}
.block-container .bc-quote, .block-container .bc-evidence {{ background: rgba(231,155,208,.08); color: {DARK_TEXT}; }}
.block-container .bc-trail .node {{ background: #20232B; border-color: {DARK_LINE}; }}
.block-container .bc-trail .node .v {{ color: {DARK_TEXT}; }}
.block-container .bc-trail .link {{ border-top-color: #3A3F4B; }}
.block-container .bc-tl {{ border-left-color: {DARK_LINE}; }}
.block-container .bc-tl .ev::before {{ background: {DARK_BG}; }}
.block-container .bc-tl .ev .a, .block-container .bc-trail .node .v {{ color: {DARK_TEXT}; }}
.block-container .bc-trail .node.missing .v {{ color: #F7A5AA; }}
.block-container .bc-table {{ background: {DARK_PANEL}; border-color: {DARK_LINE}; }}
.block-container .bc-table th {{ background: #20232B; color: {DARK_MUTED}; border-bottom-color: {DARK_LINE}; }}
.block-container .bc-table td {{ border-bottom-color: {DARK_LINE}; color: {DARK_TEXT}; }}
.block-container .bc-table tr.hl td {{ background: rgba(240,207,114,.08); }}
.block-container .bc-specimen {{ background: #20232B; border-color: {DARK_LINE}; }}
.block-container .bc-specimen .rule {{ color: #fff; }}
.block-container .bc-empty {{ background: {DARK_PANEL}; border-color: #3A3F4B; }}
.block-container .bc-empty b {{ color: #fff; }}
.block-container .bc-illustrative {{ background: rgba(240,207,114,.12); color: {YELLOW}; }}
.block-container .bc-split {{ background: {DARK_PANEL}; border-color: {DARK_LINE}; }}
.block-container .bc-split .sv-verdict, .block-container .bc-split .sv-gl {{ color: #fff; }}
.block-container .bc-split .sv-col.split {{ background: rgba(240,207,114,.10); border-color: {YELLOW}; }}
.block-container .bc-split .sv-pass {{ background: rgba(127,211,160,.16); color: #9FE3BA; }}
.block-container .bc-split .sv-fail {{ background: rgba(241,125,131,.16); color: #F7A5AA; }}
.block-container .bc-split .sv-unclear {{ background: rgba(240,207,114,.16); color: {YELLOW}; }}
.block-container .v-pass {{ background: rgba(127,211,160,.16); color: #9FE3BA; }}
.block-container .v-fail {{ background: rgba(241,125,131,.16); color: #F7A5AA; }}
.block-container .v-unclear {{ background: rgba(240,207,114,.16); color: {YELLOW}; }}
.block-container .v-review {{ background: rgba(231,155,208,.16); color: #F1BCE0; }}
.block-container .bc-page {{ background: #F7F6F2; }}
.block-container .bc-page, .block-container .bc-page p, .block-container .bc-page span {{ color: #2A2E2A !important; }}
.st-key-tour-offer {{ background: #20232B; }}
[role="listbox"] {{ background: #20232B !important; }}
[role="listbox"] [role="option"] {{ color: {DARK_TEXT} !important; }}
[role="listbox"] [role="option"]:hover, [role="listbox"] [role="option"][data-focused] {{ background: #2C303A !important; }}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def dark():
    """Switch the current page to the dark investigation design (RuleProbe, Brand Knowledge Graph)."""
    st.markdown(DARK_CSS, unsafe_allow_html=True)
