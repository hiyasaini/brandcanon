"""Turn a Markdown report into a clean A4 PDF (headings, bullets, quotes, paragraphs). Used by the health check and audit reports."""
import io
import re
from xml.sax.saxutils import escape


def _safe(text):
    """The built-in PDF fonts cover Western characters; anything else is replaced rather than crashing."""
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _inline(text):
    t = escape(_safe(text))
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w])_(.+?)_(?![\w])", r"<i>\1</i>", t)
    return re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", t)


def from_markdown(md: str, footer: str = "BrandCanon") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    ink, muted, green = colors.HexColor("#242824"), colors.HexColor("#5B645E"), colors.HexColor("#263A32")
    st = {
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=green, spaceAfter=8),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=green, spaceBefore=12, spaceAfter=5),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=ink, spaceBefore=9, spaceAfter=3),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=ink, alignment=TA_LEFT, spaceAfter=4),
        "li": ParagraphStyle("li", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=ink, leftIndent=12, bulletIndent=2, spaceAfter=2),
        "q": ParagraphStyle("q", fontName="Helvetica-Oblique", fontSize=9.5, leading=13.5, textColor=muted, leftIndent=10,
                            borderPadding=(3, 3, 3, 8), backColor=colors.HexColor("#F3F6F2"), spaceBefore=3, spaceAfter=6),
    }
    story = []
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            story.append(Spacer(1, 3))
        elif line.startswith("### "):
            story.append(Paragraph(_inline(line[4:]), st["h3"]))
        elif line.startswith("## "):
            story.append(Paragraph(_inline(line[3:]), st["h2"]))
        elif line.startswith("# "):
            story.append(Paragraph(_inline(line[2:]), st["h1"]))
        elif line.startswith("> "):
            story.append(Paragraph(_inline(line[2:]), st["q"]))
        elif re.match(r"^\s*[-*] ", line):
            story.append(Paragraph(_inline(re.sub(r"^\s*[-*] ", "", line)), st["li"], bulletText="•"))
        else:
            story.append(Paragraph(_inline(line), st["p"]))

    def page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(muted)
        canvas.drawString(20 * mm, 11 * mm, _safe(footer))
        canvas.drawRightString(A4[0] - 20 * mm, 11 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
                      title="BrandCanon report").build(story or [Paragraph("Empty report.", st["p"])], onFirstPage=page, onLaterPages=page)
    return buf.getvalue()
