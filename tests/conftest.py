import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Fresh database, a NovaTech workspace and one user per role. Gemini is forced off for determinism."""
    monkeypatch.setenv("BRANDCANON_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRANDCANON_OFFLINE", "1")
    monkeypatch.setenv("AI_PROVIDER", "deterministic")
    import config
    from database import db, repositories as repo
    db.reset_connections()
    db.init()
    if not (config.SAMPLE_DIR / "NovaTech_Product_Specification.pdf").exists():
        from scripts import make_sample_documents
        make_sample_documents.build()
    ws = repo.get_or_create_workspace("NovaTech test", True)
    users = {r: repo.get_or_create_user(ws, r.split()[0], r) for r in ("Brand Manager", "Reviewer", "Creator")}
    yield {"ws": ws, "bm": users["Brand Manager"], "rv": users["Reviewer"], "cr": users["Creator"], "tmp": tmp_path}
    db.reset_connections()


@pytest.fixture()
def loaded(env):
    """Workspace with the four NovaTech sample documents uploaded and official rules approved."""
    import config
    from modules import brand_constitution, document_ingestion
    for f in sorted(config.SAMPLE_DIR.iterdir()):
        document_ingestion.ingest(env["ws"], env["bm"], f.name, f.read_bytes(), use_ai=False)
    brand_constitution.approve_all_pending(env["ws"], env["bm"], 3)
    return env


def rule_with(ws, fragment):
    from database import repositories as repo
    return next(r for r in repo.list_rules(ws) if fragment.lower() in r["text"].lower())


def docx(*paragraphs):
    """Bytes of a small Word document (uploads are PDF/DOCX only)."""
    import io
    from docx import Document
    d = Document()
    for t in paragraphs:
        d.add_paragraph(t)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
