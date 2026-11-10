"""Turn uploaded PDF and DOCX files into (location, text) pages, preserving page or section numbers.

BrandCanon is a manually managed, document-based platform: it only reads files a person uploads. There is no web
fetching, scraping or automated company research.
"""
import io
import re

from modules import text_features as tf


class ParseError(ValueError):
    """The document could not be read; message is safe to show to users."""


def parse_pdf(data: bytes):
    try:
        import pymupdf as fitz
    except ImportError:  # older PyMuPDF
        import fitz
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise ParseError(f"This PDF could not be opened ({str(e)[:80]}).") from e
    if doc.needs_pass:
        raise ParseError("This PDF is password-protected.")
    return [(f"p.{i + 1}", page.get_text("text")) for i, page in enumerate(doc)]


def parse_docx(data: bytes):
    from docx import Document
    try:
        d = Document(io.BytesIO(data))
    except Exception as e:
        raise ParseError(f"This Word file could not be opened ({str(e)[:80]}).") from e
    pages, buf, sec = [], [], 1
    for p in d.paragraphs:
        if p.style is not None and p.style.name.lower().startswith("heading") and buf:
            pages.append((f"§{sec}", "\n".join(buf)))
            buf, sec = [], sec + 1
        if p.text.strip():
            buf.append(p.text.strip())
    for t in d.tables:  # spec tables are common in brand docs
        rows = [" | ".join(c.text.strip() for c in r.cells) for r in t.rows]
        if rows:
            buf.append("\n".join(rows))
    if buf:
        pages.append((f"§{sec}", "\n".join(buf)))
    return pages


def parse(ext: str, data: bytes):
    if ext == ".pdf":
        return parse_pdf(data)
    if ext == ".docx":
        return parse_docx(data)
    raise ParseError(f"Unsupported file type {ext}. Upload a PDF or DOCX file.")


def split_sentences(page_text):
    """Re-join wrapped PDF lines into sentences; headings are returned separately as ('H', text)."""
    lines = [l.strip() for l in page_text.splitlines() if l.strip()]
    out, buf = [], ""
    for i, l in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        is_heading = (not re.search(r"[.!?:,]$", l) and len(l.split()) <= 7 and (not nxt or nxt[:1].isupper())
                      and ":" not in l and not l[:1].islower() and "|" not in l)
        if is_heading:
            if buf:
                out.append(("S", buf))
                buf = ""
            out.append(("H", l))
            continue
        buf = (buf + " " + l).strip()
        if re.search(r"[.!?]$", l) or "|" in l or (nxt[:1].isupper() and ":" in nxt[:30] and not l.endswith(",")):
            out.append(("S", buf))
            buf = ""
    if buf:
        out.append(("S", buf))
    res = []
    for kind, s in out:
        if kind == "H":
            res.append(("H", s))
        else:
            res += [("S", sent) for _, _, sent in tf.sentences(s)]
    return res
