"""Generate the fictional NovaTech sample documents used by demo mode and the tests.

NovaTech is a made-up company. The documents deliberately contain:
  * a vague tone rule ("friendly but professional")
  * a contradiction between an official specification (up to 12 h) and an older presentation (15 h)
  * a scoped rule conflict (formal everywhere vs casual on social media)
  * missing guidance (nothing about influencer partnerships)
Run:  python scripts/make_sample_documents.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer  # noqa: E402
from docx import Document  # noqa: E402

import config  # noqa: E402

OUT = config.SAMPLE_DIR
ss = getSampleStyleSheet()
H = ParagraphStyle("h", parent=ss["Heading2"], textColor="#23264F")
B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=10.5, leading=15)


def pdf(name, title, meta, pages):
    doc = SimpleDocTemplate(str(OUT / name), pagesize=A4, title=title)
    story = [Paragraph(title, ss["Title"]), Paragraph(meta, B), Spacer(1, 10)]
    for i, (heading, paras) in enumerate(pages):
        if i:
            story.append(PageBreak())
        story.append(Paragraph(heading, H))
        for p in paras:
            story += [Paragraph(p, B), Spacer(1, 6)]
    doc.build(story)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    pdf("NovaTech_Product_Specification.pdf", "NovaTech Product Specification",
        "Version 2.0 - Effective 15 September 2026 - Owner: Product Engineering", [
            ("About this document", [
                "This specification is the approved source for all NovaTech product facts used in marketing.",
            ]),
            ("NovaTech X1 (laptop) performance", [
                "Processor: NovaCore 8-core, up to 3.2 GHz.",
                "Memory: 16 GB.",
                "Storage: 512 GB SSD.",
                "Display: 14-inch 2.8K OLED.",
                "Weight: 1.29 kg.",
            ]),
            ("NovaTech X1 (laptop) power", [
                "Battery life: Up to 12 hours under specified testing conditions (local video playback at 150 nits).",
                "Fast charging: 0 to 50% in 30 minutes with the included 65 W charger.",
                "Warranty: 1 year limited warranty.",
            ]),
            ("NovaTech Pulse (smartphone)", [
                "Battery life: Up to 2 days of typical use.",
                "Main camera: 50 MP.",
                "Storage: 256 GB.",
            ]),
        ])
    pdf("NovaTech_Marketing_Presentation_2025.pdf", "NovaTech X1 Marketing Presentation (Q4 2025)",
        "Version 0.9 - 1 November 2025 - Owner: Sales", [
            ("Key selling points", [
                "Battery life: 15 hours.",
                "Weight: 1.2 kg.",
                "Pitch the X1 as the most powerful laptop in its class.",
                "Make every post exciting and use plenty of emojis.",
            ]),
        ])
    pdf("NovaTech_Brand_Guidelines.pdf", "NovaTech Brand Guidelines",
        "Version 1.2 - Effective 1 August 2026 - Owner: Brand Office", [
            ("Who we are", [
                "Our brand personality is innovative, trustworthy and approachable.",
            ]),
            ("Voice and tone", [
                "Maintain a friendly but professional tone.",
                "Make promotional content exciting and persuasive.",
                "Always use formal communication.",
                "Use casual language in every social media post.",
                "Customer support emails should be clear and concise, with sentences under 25 words.",
            ]),
            ("Terminology", [
                "Never use the word \"unbreakable\" because no device can be guaranteed against damage.",
                "Do not use \"risk-free\" or \"guaranteed results\" in any communication.",
                "Always write \"NovaTech X1\" in full.",
                "Do not use \"Nova X1\" or \"the X-One\".",
            ]),
            ("Visual identity and accessibility", [
                "Primary colour: Nova Indigo #23264F.",
                "Accent colour: Signal Coral #D9705A.",
                "Text must meet a contrast ratio of at least 4.5:1 against its background.",
                "All published images must include alternative text.",
            ]),
            ("Messaging", [
                "NovaTech X1 is positioned for students and professionals seeking reliable everyday performance.",
                "Instagram captions should be under 150 words and end with a clear next step.",
            ]),
        ])
    d = Document()
    d.add_heading("NovaTech Marketing Policy", 0)
    d.add_paragraph("Version 1.1 - Effective 1 July 2026 - Owner: Legal and Marketing")
    d.add_heading("Claims", 1)
    d.add_paragraph("Comparative or superlative claims such as \"best\", \"most powerful\" or \"fastest\" require documented evidence approved by Legal.")
    d.add_paragraph("Never present a performance figure without its testing qualifier.")
    d.add_paragraph("Avoid absolute promotional promises that cannot be substantiated.")
    d.add_heading("Promotions", 1)
    d.add_paragraph("Discount and offer posts must state the end date of the offer.")
    d.add_paragraph("Do not use pressure phrases such as \"buy now or regret it\".")
    d.save(OUT / "NovaTech_Marketing_Policy.docx")
    return sorted(p.name for p in OUT.iterdir())


if __name__ == "__main__":
    print("Written:", build())
