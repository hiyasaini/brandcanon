"""LIVE Gemini smoke tests — they call the real API and use a little quota.

They run only when live Gemini is configured (AI_PROVIDER=gemini and GEMINI_API_KEY in .env or the environment);
otherwise every test here is skipped. Run them on their own with:

    bash scripts/run_live_tests.sh        (or: pytest -m live -v)
"""
import pytest

import config
from services import gemini_service as gs, validation_service as vs

LIVE_READY = config.ai_provider() == "gemini" and bool(config.gemini_key()) and not config.offline_forced()
pytestmark = [pytest.mark.live,
              pytest.mark.skipif(not LIVE_READY, reason="Live Gemini not configured: set AI_PROVIDER=gemini and "
                                                        "GEMINI_API_KEY in .env to run the live smoke tests.")]


@pytest.fixture()
def live_db(tmp_path, monkeypatch):
    monkeypatch.setenv("BRANDCANON_DB", str(tmp_path / "live.db"))
    from database import db
    db.reset_connections()
    db.init()
    yield
    db.reset_connections()


def test_live_connection(live_db):
    out = gs.check_connection()
    assert out["ok"], f"Gemini connection failed ({out.get('kind')}): {out.get('message')}"
    assert out["reply"].strip()
    assert config.gemini_key() not in str(out)


def test_live_structured_output_is_validated(live_db):
    with gs.tracking() as src:
        res = gs.generate("Rewrite this rule so it is measurable: 'Keep posts short.' "
                          'Return JSON {"rule": str}', vs.Clarification, cache=False)
    assert isinstance(res, vs.Clarification) and len(res.rule) >= 5
    assert src == ["live"]


def test_live_content_audit_end_to_end(live_db):
    from database import repositories as repo
    from modules import brand_constitution, content_audit, demo, document_ingestion
    ws = repo.get_or_create_workspace("Live smoke test")
    bm = repo.get_or_create_user(ws, "Tester", "Brand Manager")
    for f in sorted(config.SAMPLE_DIR.iterdir()):
        document_ingestion.ingest(ws, bm, f.name, f.read_bytes(), use_ai=False)
    brand_constitution.approve_all_pending(ws, bm, 3)
    res = content_audit.run(ws, demo.DEMO_POST, "Instagram", "Social media caption", "NovaTech X1", use_ai=True)
    assert res["ai_error"] is None, res["ai_error"]
    assert res["engine"].startswith("Live Gemini"), res["engine"]
    for f in res["findings"]:
        if f["engine"].startswith("Live Gemini"):
            assert f["quote"] in demo.DEMO_POST      # every AI quote exists in the content


def test_live_invalid_key_is_reported_clearly(live_db, monkeypatch):
    bad = "AIza" + "x" * 35
    monkeypatch.setenv("GEMINI_API_KEY", bad)
    with pytest.raises(gs.GeminiError) as e:
        gs.generate('Return JSON {"rule": "Use one emoji at most."}', vs.Clarification, cache=False)
    assert e.value.kind == "invalid_key", (e.value.kind, e.value.message)
    assert bad not in str(e.value) and bad not in e.value.detail
