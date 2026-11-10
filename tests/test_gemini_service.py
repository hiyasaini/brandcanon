"""Mocked tests for the Gemini integration. No network: the SDK call is replaced by fakes.

They check provider selection, validation before use, error classification, that the key never leaks, and that a Gemini
failure is reported (never silently replaced by made-up output).
"""
import json
import re
from pathlib import Path

import pytest

try:  # google-genai 3.x uses httpx2; older versions use httpx
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx
from google.genai import errors as ge

from tests.conftest import rule_with
from database import repositories as repo
from modules import approval_workflow as aw, content_audit, decision_memory as dm, demo, knowledge_extraction as kx, rule_probe
from services import gemini_service as gs, validation_service as vs

FAKE_KEY = "test-only-not-a-real-gemini-key-0123456789"


@pytest.fixture()
def gemini_on(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    monkeypatch.setenv("BRANDCANON_OFFLINE", "0")
    monkeypatch.setattr(gs, "RETRY_DELAYS", (0, 0))   # no real waiting in tests
    return monkeypatch


def api_error(code, message, status):
    cls = ge.ClientError if code < 500 else ge.ServerError
    return cls(code, {"error": {"code": code, "message": message, "status": status}})


# ------------------------------------------------------------------ selection and status
def test_provider_selection(env, monkeypatch):
    monkeypatch.setenv("BRANDCANON_OFFLINE", "0")
    monkeypatch.setenv("AI_PROVIDER", "deterministic")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    assert gs.status()["mode"] == "deterministic" and not gs.enabled()
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    assert gs.status()["mode"] == "gemini" and gs.enabled()
    monkeypatch.setenv("GEMINI_MODEL", "gemini-other")
    assert gs.model() == "gemini-other" and gs.live_label() == "Live Gemini · gemini-other"
    monkeypatch.setenv("GEMINI_API_KEY", "")
    st = gs.status()
    assert st["mode"] == "misconfigured" and "GEMINI_API_KEY" in st["problem"]
    with pytest.raises(gs.GeminiError) as e:
        gs.generate("x", vs.Clarification, cache=False)
    assert e.value.kind == "not_configured"
    monkeypatch.setenv("AI_PROVIDER", "openai")
    assert "not recognised" in gs.status()["problem"]


def test_demo_suspension_labels_demo_fallback(env, gemini_on):
    with gs.suspended():
        assert not gs.enabled()
        assert gs.deterministic_label().startswith("Demo fallback")
    assert gs.enabled()


# ------------------------------------------------------------------ validation before use
def test_malformed_output_retried_then_rejected(env, gemini_on):
    calls = []

    def bad(*a):
        calls.append(1)
        return "this is not json"
    with pytest.raises(gs.GeminiError) as e:
        gs.generate("x", vs.Clarification, cache=False, _caller=bad)
    assert e.value.kind == "malformed" and len(calls) == 2 and "discarded" in e.value.message
    with pytest.raises(gs.GeminiError) as e:
        gs.generate("x", vs.Clarification, cache=False, _caller=lambda *a: '{"wrong": 1}')
    assert "expected structure" in e.value.message
    out = gs.generate("x", vs.Clarification, cache=False, _caller=lambda *a: '```json\n{"rule": "Use at most one emoji."}\n```')
    assert out.rule == "Use at most one emoji."


def test_cache_is_labelled_as_cached(env, gemini_on):
    gemini_on.setattr(gs, "_call", lambda *a: '{"rule": "Use at most one emoji per post."}')
    with gs.tracking() as src:
        gs.generate("cache me", vs.Clarification)
    assert gs.label_for(src) == "Live Gemini · gemini-test-model"
    gemini_on.setattr(gs, "_call", lambda *a: pytest.fail("cache should have been used"))
    with gs.tracking() as src:
        gs.generate("cache me", vs.Clarification)
    assert "cached response" in gs.label_for(src)


# ------------------------------------------------------------------ error classification
@pytest.mark.parametrize("exc,kind", [
    (api_error(400, "API key not valid. Please pass a valid API key.", "INVALID_ARGUMENT"), "invalid_key"),
    (api_error(403, "Method doesn't allow unregistered callers.", "PERMISSION_DENIED"), "invalid_key"),
    (api_error(429, "Resource has been exhausted (e.g. check quota).", "RESOURCE_EXHAUSTED"), "quota"),
    (api_error(404, "models/gemini-9 is not found for API version v1beta.", "NOT_FOUND"), "model_unavailable"),
    (api_error(503, "The model is overloaded.", "UNAVAILABLE"), "service"),
    (api_error(400, "Invalid JSON payload.", "INVALID_ARGUMENT"), "rejected"),
    (httpx.ConnectError("connection refused"), "network"),
    (httpx.ReadTimeout("timed out"), "network"),
    (ValueError("weird"), "unknown"),
])
def test_errors_are_classified_and_reported(env, gemini_on, exc, kind):
    def raiser(*a):
        raise exc
    with pytest.raises(gs.GeminiError) as e:
        gs.generate("x", vs.Clarification, cache=False, _caller=raiser)
    assert e.value.kind == kind
    assert gs.last_error_info()["kind"] == kind and gs.last_error() == e.value.message
    assert e.value.__cause__ is None   # the raw SDK traceback is not chained into what gets shown


def test_busy_service_is_retried_then_succeeds(env, gemini_on):
    calls = []

    def flaky(*a):
        calls.append(1)
        if len(calls) < 3:
            raise api_error(504, "Deadline expired before operation could complete.", "DEADLINE_EXCEEDED")
        return json.dumps({"rule": "Use a warm, plain tone without slang."})
    out = gs.generate("x", vs.Clarification, cache=False, _caller=flaky)
    assert len(calls) == 3 and out is not None


def test_retries_give_up_and_report_attempts(env, gemini_on):
    calls = []

    def busy(*a):
        calls.append(1)
        raise api_error(504, "Deadline expired before operation could complete.", "DEADLINE_EXCEEDED")
    with pytest.raises(gs.GeminiError) as e:
        gs.generate("x", vs.Clarification, cache=False, _caller=busy)
    assert len(calls) == 3 and e.value.kind == "service" and "tried 3 times" in e.value.message


def test_quota_errors_are_not_retried(env, gemini_on):
    calls = []

    def q(*a):
        calls.append(1)
        raise api_error(429, "Quota exceeded", "RESOURCE_EXHAUSTED")
    with pytest.raises(gs.GeminiError):
        gs.generate("x", vs.Clarification, cache=False, _caller=q)
    assert len(calls) == 1


def test_api_key_never_appears_in_errors(env, gemini_on):
    def leaky(*a):
        raise httpx.ConnectError(f"failed GET https://x/v1?key={FAKE_KEY} using {FAKE_KEY}")
    with pytest.raises(gs.GeminiError) as e:
        gs.generate("x", vs.Clarification, cache=False, _caller=leaky)
    shown = json.dumps(gs.last_error_info()) + str(e.value) + e.value.detail
    assert FAKE_KEY not in shown and "[redacted" in shown
    assert gs.scrub(f"token {FAKE_KEY}") == "token [redacted-key]"
    shaped = "AIza" + "Q" * 35   # anything shaped like a Google key is removed too, even if it is not the configured one
    assert gs.scrub(f"leak {shaped}") == "leak [redacted-key]"


def test_check_connection_reports_failure_without_key(env, gemini_on):
    class Boom:
        class models:
            @staticmethod
            def generate_content(**kw):
                raise api_error(400, "API key not valid. Please pass a valid API key.", "INVALID_ARGUMENT")
    gemini_on.setattr(gs, "_client_obj", lambda: Boom)
    out = gs.check_connection()
    assert out["ok"] is False and out["kind"] == "invalid_key" and FAKE_KEY not in json.dumps(out)


def test_check_connection_success(env, gemini_on):
    class Resp:
        text = "Hello from the test double."

    class Ok:
        class models:
            @staticmethod
            def generate_content(**kw):
                assert kw["model"] == "gemini-test-model"
                return Resp()
    gemini_on.setattr(gs, "_client_obj", lambda: Ok)
    out = gs.check_connection()
    assert out["ok"] and out["reply"].startswith("Hello")


# ------------------------------------------------------------------ no silent fallback in features
def quota(*a):
    raise api_error(429, "Quota exceeded", "RESOURCE_EXHAUSTED")


def test_audit_reports_gemini_failure(loaded, gemini_on):
    gemini_on.setattr(gs, "_call", quota)
    res = content_audit.run(loaded["ws"], demo.DEMO_POST, "Instagram", "Social media caption", "NovaTech X1")
    assert res["engine"] == "Deterministic logic — Gemini failed: quota or rate limit reached"
    assert "429" in res["ai_error"]
    assert any(f["classification"] == "Contradicted" for f in res["findings"])   # deterministic checks still ran
    assert all(not f["engine"].startswith("Live Gemini") for f in res["findings"])


def test_audit_when_gemini_requested_but_not_configured(loaded, monkeypatch):
    monkeypatch.setenv("BRANDCANON_OFFLINE", "0")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    res = content_audit.run(loaded["ws"], "Hello", "Instagram", "Social media caption", "NovaTech X1")
    assert res["engine"].endswith("Gemini not configured") and "GEMINI_API_KEY" in res["ai_error"]


def test_audit_with_live_gemini_findings_validated(loaded, gemini_on):
    text = "NovaTech X1 is a total vibe, trust us."

    def fake(prompt, t):
        return json.dumps({"findings": [
            {"quote": "a total vibe", "category": "Tone", "severity": "low", "rule_code": "R999", "message": "Too casual.",
             "suggestion": "a dependable choice"},
            {"quote": "not in the text", "category": "Tone", "severity": "high", "message": "Invented quote."},
            {"quote": "trust us", "category": "Unsupported claim", "severity": "medium", "message": "No evidence.",
             "suggestion": "rated 99% by everyone"}]})
    gemini_on.setattr(gs, "_call", fake)
    res = content_audit.run(loaded["ws"], text, "Instagram", "Social media caption", "NovaTech X1")
    ai = [f for f in res["findings"] if f["engine"].startswith("Live Gemini")]
    assert res["engine"].startswith("Live Gemini · gemini-test-model")
    assert {f["quote"] for f in ai} == {"a total vibe", "trust us"}          # invented quote discarded
    assert next(f for f in ai if f["quote"] == "trust us")["suggestion"] == ""  # ungrounded "99%" suggestion dropped


def test_extraction_failure_is_reported(env, gemini_on):
    gemini_on.setattr(gs, "_call", quota)
    pages = [("p.1", "NovaTech Guide\nAlways use a friendly tone. Never say unbreakable.")]
    *_, engine, err = kx.extract(pages, use_ai=True)
    assert engine.startswith("Deterministic logic — Gemini failed") and "429" in err


def test_extraction_with_gemini_keeps_only_text_in_document(env, gemini_on):
    gemini_on.setattr(gs, "_call", lambda *a: json.dumps({
        "rules": [{"text": "Always use a friendly tone.", "category": "Brand tone", "scope": "All content"},
                  {"text": "Invented rule that is not in the document.", "category": "Brand tone"}],
        "facts": [], "terms": []}))
    passages, rules, facts, terms, engine, err = kx.extract([("p.1", "Always use a friendly tone. Keep posts short.")])
    assert engine.startswith("Live Gemini") and err is None
    assert [r["text"] for r in rules] == ["Always use a friendly tone."]


def test_ruleprobe_failure_falls_back_with_label(loaded, gemini_on):
    gemini_on.setattr(gs, "_call", quota)
    r = rule_with(loaded["ws"], "friendly but professional")
    tid = rule_probe.run_test(loaded["ws"], loaded["bm"], r["id"])
    t = repo.latest_test(r["id"])
    assert t["id"] == tid and t["engine"].startswith("Deterministic logic — Gemini failed: quota")
    assert t["classification"] == "Ambiguous rule"


def test_ruleprobe_gemini_generates_cases_for_unknown_words(loaded, gemini_on):
    ws = loaded["ws"]
    from database import db
    r = rule_with(ws, "friendly but professional")
    db.update("brand_rules", r["id"], text="Copy must feel punchy.", constraints_json="{}")

    def fake(prompt, t):
        if "undefined words" in prompt:
            return json.dumps({"baseline": "NovaTech X1 is available today.", "variants": [
                {"aspect": "punchy", "level": 1, "example": "NovaTech X1 is here today."},
                {"aspect": "punchy", "level": 2, "example": "NovaTech X1. Here. Now."},
                {"aspect": "made-up", "level": 1, "example": "Should be dropped."}]})
        if "Reading: STRICT" in prompt:
            return json.dumps({"results": [{"id": i, "verdict": "fail" if i == 3 else "pass", "reason": "s"} for i in (1, 2, 3)]})
        if "Reading: LENIENT" in prompt:
            return json.dumps({"results": [{"id": i, "verdict": "pass", "reason": "l"} for i in (1, 2, 3)]})
        return json.dumps({"rule": "Copy must use sentences under 12 words and active verbs."})
    gemini_on.setattr(gs, "_call", fake)
    tid = rule_probe.run_test(ws, loaded["bm"], r["id"])
    t, cases = repo.latest_test(r["id"]), repo.test_cases(tid)
    assert t["engine"].startswith("Live Gemini") and "examples and verdicts" in t["engine"]
    assert [c["dimension"] for c in cases] == ["baseline", "ai:punchy", "ai:punchy"]
    assert t["classification"] == "Ambiguous rule" and "12 words" in t["recommendation"]


def test_ai_rewrite_is_grounded(loaded, gemini_on):
    ws = loaded["ws"]
    sid, _, rid = aw.create_draft(ws, loaded["cr"], "t", demo.DEMO_POST, "Social media caption", "Instagram", "NovaTech X1",
                                  use_ai=False)
    fs = repo.findings(rid)
    gemini_on.setattr(gs, "_call", lambda *a: json.dumps({"text": "NovaTech offers up to 18 hours of battery life!", "changes": []}))
    with pytest.raises(gs.GeminiError) as e:
        content_audit.ai_rewrite(ws, demo.DEMO_POST, fs, "NovaTech X1", "Instagram")
    assert e.value.kind == "ungrounded" and "18" in e.value.message
    good = "NovaTech offers up to 12 hours of battery life under specified testing conditions and can support your productivity!"
    gemini_on.setattr(gs, "_call", lambda *a: json.dumps({"text": good, "changes": ["Battery claim matched to spec"]}))
    out = content_audit.ai_rewrite(ws, demo.DEMO_POST, fs, "NovaTech X1", "Instagram")
    assert out["text"] == good and out["engine"].startswith("Live Gemini")


def test_precedent_summary_rejects_unknown_ids(env, gemini_on):
    precedents = [{"id": 7, "created_at": "2026-11-01", "decision": "Finding upheld", "reviewer_name": "Kavya",
                   "claim_text": "15 hours", "channel": "Instagram", "product": "X1", "explanation": "Spec says 12 h", "stale": False}]
    gemini_on.setattr(gs, "_call", lambda *a: json.dumps({"summary": "An earlier reviewer corrected the same claim.", "decision_ids": [7, 99]}))
    with pytest.raises(gs.GeminiError) as e:
        dm.summarise_precedents({"quote": "15 hours", "message": "m"}, precedents)
    assert e.value.kind == "ungrounded"
    gemini_on.setattr(gs, "_call", lambda *a: json.dumps({"summary": "An earlier reviewer corrected the same claim.", "decision_ids": [7]}))
    assert dm.summarise_precedents({"quote": "15 hours", "message": "m"}, precedents)["decision_ids"] == [7]


def test_features_refuse_when_gemini_off(env):
    with pytest.raises(gs.GeminiError) as e:
        content_audit.ai_rewrite(env["ws"], "x", [{"classification": "Violation", "quote": "", "message": "m", "suggestion": ""}])
    assert e.value.kind == "not_configured"


# ------------------------------------------------------------------ secrets hygiene
def test_no_api_keys_committed():
    root = Path(__file__).resolve().parent.parent
    skip = {".venv", "__pycache__", ".git", "data"}
    pattern = re.compile(r"AIza[0-9A-Za-z_\-]{35}")
    hits = []
    for p in root.rglob("*"):
        if p.is_file() and not (set(p.parts) & skip) and p.name != ".env" and p.suffix in {".py", ".md", ".toml", ".txt", ".example", ".sh", ".json", ""}:
            if pattern.search(p.read_text(errors="ignore")):
                hits.append(str(p))
    assert not hits, f"Possible API key committed in: {hits}"
    gi = (root / ".gitignore").read_text()
    assert ".env" in gi and "secrets.toml" in gi


# ------------------------------------------------------------------ automatic start-up check and provider default
def test_gemini_switches_on_when_only_a_key_is_set(monkeypatch):
    import config
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("BRANDCANON_OFFLINE", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    assert config.ai_provider() == "gemini"
    monkeypatch.delenv("GEMINI_API_KEY")
    assert config.ai_provider() == "deterministic"          # no key: nothing to switch on
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("AI_PROVIDER", "deterministic")      # an explicit choice always wins
    assert config.ai_provider() == "deterministic"


def test_background_check_verifies_without_a_button(env, gemini_on):
    import time as _t

    class Resp:
        text = "ok"

    class Ok:
        class models:
            @staticmethod
            def generate_content(**kw):
                return Resp()
    gemini_on.setattr(gs, "_client_obj", lambda: Ok)
    gs._state["last_check"] = None
    assert gs.verify_in_background() is True
    for _ in range(100):
        if not gs.checking():
            break
        _t.sleep(0.05)
    assert not gs.checking() and gs.stats()["last_check"]["ok"] is True


def test_background_check_not_started_when_gemini_is_off(env, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "deterministic")
    assert gs.verify_in_background() is False and not gs.checking()


def test_public_mode_flag_and_default_database_path(monkeypatch):
    import config
    monkeypatch.delenv("BRANDCANON_PUBLIC", raising=False)
    assert config.public_mode() is False
    monkeypatch.setenv("BRANDCANON_PUBLIC", "1")
    assert config.public_mode() is True
    monkeypatch.setenv("BRANDCANON_DB", "/tmp/x_test.db")
    assert str(config.db_path()) == "/tmp/x_test.db"        # outside a Streamlit session the configured path is used
