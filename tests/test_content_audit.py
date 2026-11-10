from database import repositories as repo
from modules import content_audit as ca
from modules.demo import DEMO_POST


def _run(env, text, channel="Website"):
    return ca.run(env["ws"], text, channel, "Website copy", "NovaTech X1", use_ai=False)


def _find(res, cls):
    return [f for f in res["findings"] if f["classification"] == cls]


def test_supported_claim_is_verified(loaded):
    res = _run(loaded, "Enjoy up to 12 hours of battery life under specified testing conditions.")
    assert res["status"] == "No issues found"
    v = _find(res, "Verified")
    assert v and v[0]["evidence_source"].startswith("NovaTech Product Specification")


def test_contradicted_numeric_claim_cites_page(loaded):
    res = _run(loaded, DEMO_POST, "Instagram")
    f = _find(res, "Contradicted")[0]
    assert f["quote"] == "15 hours of battery life" and f["severity"] == "high"
    assert "p.3" in f["evidence_source"] and "Up to 12 hours" in f["evidence_text"]
    assert f["suggestion"] == "up to 12 hours of battery life under specified testing conditions"
    g = next(x for x in res["findings"] if x["quote"] == "guarantees")
    assert g["classification"] == "Unsupported" and g["suggestion"] == "offers" and "guarantee" in g["message"].lower()
    assert f["root_cause"] == "Source conflict", "the 15 h figure exists in the older presentation"


def test_unsupported_promotional_claim(loaded):
    res = _run(loaded, DEMO_POST, "Instagram")
    u = [f for f in _find(res, "Unsupported") if f["category"] == "Claims" and "transform" in f["quote"]]
    assert u and "completely transform your productivity" in u[0]["quote"] and u[0]["severity"] == "medium"
    assert "false" not in u[0]["message"].lower() or "not false" in u[0]["message"].lower()


def test_missing_qualifier(loaded):
    f = _find(_run(loaded, "Get 12 hours of battery life on NovaTech X1."), "Unsupported")[0]
    assert "qualifier" in f["message"] and f["suggestion"].startswith("up to 12 hours")


def test_terminology_violation(loaded):
    res = _run(loaded, "The unbreakable Nova X1 is here.")
    terms = [f for f in res["findings"] if f["category"] == "Terminology"]
    assert {f["quote"] for f in terms} == {"unbreakable", "Nova X1"}
    assert {f["suggestion"] for f in terms} == {"durable", "NovaTech X1"}


def test_tone_mismatch(loaded):
    res = _run(loaded, "Heyyy besties, NovaTech X1 is literally insane!!!", "Instagram")
    tone = [f for f in res["findings"] if f["category"] == "Tone"]
    assert tone and tone[0]["classification"] in ("Violation", "Needs review")


def test_superlative_without_evidence_is_unverifiable_not_false(loaded):
    f = _find(_run(loaded, "The fastest laptop on the market."), "Unverifiable")[0]
    assert "not false" in f["message"] and f["rule_id"]


def test_missing_evidence_is_a_knowledge_gap(env):
    """No documents at all: claims are reported as unverifiable knowledge gaps, never as false."""
    res = ca.run(env["ws"], "The best laptop ever made.", "Website", "Website copy", None, use_ai=False)
    f = _find(res, "Unverifiable")[0]
    assert f["root_cause"] == "Knowledge gap" and "No approved evidence" in f["evidence_source"]


def test_apply_suggestions_keeps_message(loaded):
    res = _run(loaded, DEMO_POST, "Instagram")
    reps = {i: f["suggestion"] for i, f in enumerate(res["findings"]) if f["suggestion"]}
    fixed = ca.apply_suggestions(DEMO_POST, res["findings"], reps)
    assert fixed == "NovaTech offers up to 12 hours of battery life under specified testing conditions and can support your productivity!"
    again = _run(loaded, fixed, "Website")
    assert not [f for f in again["findings"] if f["classification"] in ("Contradicted", "Unsupported", "Unverifiable")]
    _ = repo


def test_visual_audit_checks():
    import io
    from PIL import Image, ImageDraw
    from modules import visual_audit as va
    im = Image.new("RGB", (800, 500), "#2E3170")
    ImageDraw.Draw(im).rectangle([300, 200, 380, 260], fill="#FFFFFF")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    logo = Image.new("RGB", (80, 60), "#FFFFFF")
    ImageDraw.Draw(logo).rectangle([0, 0, 79, 59], outline="#2E3170", width=1)
    lbuf = io.BytesIO()
    logo.save(lbuf, "PNG")
    assert va.contrast("#FFFFFF", "#000000") == 21.0
    res = va.audit(buf.getvalue(), "Instagram", alt_text="", palette={"Indigo": "#2E3170"}, min_contrast=4.5,
                   text_hex="#AAAAAA", bg_hex="#BBBBBB")
    msgs = " ".join(m for _, m in res["findings"])
    assert "not a standard Instagram size" in msgs and "alternative text" in msgs and "below the brand minimum" in msgs
    ok = va.audit(buf.getvalue(), "Website", alt_text="Laptop on a desk", text_hex="#FFFFFF", bg_hex="#2E3170",
                  logo_data=lbuf.getvalue())
    assert ok["contrast"] > 4.5 and ok["logo_score"] is not None
