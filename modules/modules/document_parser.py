"""Turn uploaded PDF and DOCX files into (location, text) pages, preserving page or section numbers.

BrandCanon is a manually managed, document-based platform: it only reads files a person uploads. There is no web
fetching, scraping or automated company research.
"""
import io
import re

from modules import text_features as tf


class ParseError(ValueError):
    """The document could not be read; message is safe to show to users."""


def _ocr_tool():
    import shutil
    return shutil.which("tesseract")


def _ocr_page(page):
    """Read a scanned page with Tesseract. Returns text, or None when no OCR engine is installed."""
    import subprocess
    import tempfile
    exe = _ocr_tool()
    if not exe:
        return None
    pix = page.get_pixmap(dpi=200)
    with tempfile.TemporaryDirectory() as d:
        img = f"{d}/page.png"
        pix.save(img)
        try:
            r = subprocess.run([exe, img, "stdout", "--psm", "3"], capture_output=True, text=True, timeout=90)
        except (subprocess.TimeoutExpired, OSError):
            return ""
    return r.stdout if r.returncode == 0 else ""


def _page_text(page):
    """Page text with table rows kept as 'a | b | c' lines instead of a jumble of cells."""
    try:
        tables = [t for t in page.find_tables().tables if t.row_count >= 2 and t.col_count >= 2]
    except Exception:  # noqa: BLE001 - table detection is best effort; plain text is always available
        tables = []
    if not tables:
        return page.get_text("text")
    boxes = [fitz_rect(t.bbox) for t in tables]
    parts = []   # (y, text)
    for b in page.get_text("blocks"):
        r = fitz_rect(b[:4])
        if b[6] == 0 and not any(r.intersects(x) and (r & x).get_area() > 0.5 * r.get_area() for x in boxes):
            parts.append((b[1], b[4].strip()))
    for t, box in zip(tables, boxes):
        rows = [" | ".join(page.get_text("text", clip=fitz_rect(cell)).replace("\n", " ").strip() if cell else ""
                           for cell in row.cells) for row in t.rows]
        parts.append((box.y0, "\n".join(r for r in rows if r.replace("|", "").strip())))
    return "\n".join(x for _, x in sorted(parts, key=lambda z: z[0]) if x)


def fitz_rect(coords):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    return fitz.Rect(coords)


def parse_pdf(data: bytes, notes=None):
    """Pages of text. `notes` (a list) collects plain-language remarks, e.g. which pages were read by OCR."""
    notes = notes if notes is not None else []
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
    pages, ocr_pages, unreadable = [], [], []
    for i, page in enumerate(doc):
        text = _page_text(page)
        if len(text.strip()) < 15 and (page.get_images() or not text.strip()):
            got = _ocr_page(page)
            if got is None:
                unreadable.append(i + 1)
            elif got.strip():
                text = got
                ocr_pages.append(i + 1)
        pages.append((f"p.{i + 1}", text))
    if ocr_pages:
        notes.append(("info", "Page" + ("s " if len(ocr_pages) > 1 else " ") + ", ".join(map(str, ocr_pages[:12]))
                      + " looked like scans and were read with OCR. OCR can misread characters, so check the quoted text "
                      "against the page before approving anything."))
    if unreadable:
        notes.append(("warning", "Page" + ("s " if len(unreadable) > 1 else " ") + ", ".join(map(str, unreadable[:12]))
                      + " look like scans, but no OCR engine is installed on this server (Tesseract), so they were not read."))
    return pages


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


def parse(ext: str, data: bytes, notes=None):
    if ext == ".pdf":
        return parse_pdf(data, notes)
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
