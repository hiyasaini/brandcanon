"""Visual & accessibility review of a creative: deterministic checks always, plus Gemini Vision when it is live.

What Gemini may and may not do here:
* It may point at problems in the picture (logo use, colours, in-image text, contrast, layout, imagery) and read the text that
  is visible. Each issue may cite a brand rule only from the list we send; any other rule code is dropped and the issue is shown
  as "no brand rule cited". Boxes outside the image are dropped.
* It is never the judge of facts. The text it reads is checked by BrandCanon's own claim checker against approved facts.
* Contrast "measured" figures come only from the deterministic check; Gemini's contrast remarks are observations, labelled so.
Nothing is stored. A Gemini failure is returned as an error for the caller to show; nothing falls back silently.
"""
import io

from PIL import Image, ImageDraw, ImageFont

from database import repositories as repo
from modules import content_audit, visual_audit
from services import gemini_service, validation_service as vs

RULE_CATEGORIES = ("Visual identity", "Accessibility requirements", "Campaign instructions", "Approved claims", "Prohibited claims")
SEV_COLOUR = {"high": (214, 69, 80), "medium": (214, 154, 31), "low": (42, 157, 149)}
MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
MAX_SIDE = 1600   # larger pictures are shrunk before being sent: cheaper, and the checks do not need more


def _prepare(data):
    """(bytes, mime) for Gemini: shrunk if very large, re-encoded as PNG/JPEG so any accepted upload type works."""
    im = visual_audit.load(data)
    if max(im.size) > MAX_SIDE:
        im.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return buf.getvalue(), "image/jpeg"


def clean_box(box):
    """A usable [x, y, w, h] (fractions of the image) or None. A box that falls outside the image is dropped, not repaired."""
    try:
        x, y, w, h = [float(v) for v in box]
    except (TypeError, ValueError):
        return None
    if w <= 0.01 or h <= 0.01 or x < -0.01 or y < -0.01 or x + w > 1.02 or y + h > 1.02:
        return None
    return [max(0.0, x), max(0.0, y), min(w, 1 - max(0.0, x)), min(h, 1 - max(0.0, y))]


def review(ws, data, channel, product=None, alt_text="", _caller=None):
    """Gemini Vision review. Returns {'issues', 'text_in_image', 'text_audit', 'engine'}.
    Raises GeminiError if Gemini is off or fails (the caller shows it)."""
    rules = [r for r in repo.list_rules(ws, ("Approved",)) if r["category"] in RULE_CATEGORIES][:40]
    codes = {r["code"]: r for r in rules}
    image = _prepare(data)
    with gemini_service.tracking() as sources:
        res = gemini_service.generate(
            "You review a marketing image against the company's APPROVED RULES. Look at the picture only; do not guess facts.\n"
            f"Channel: {channel}. Product: {product or 'not specified'}. Alt text supplied: {alt_text or 'none'}.\n"
            "Report problems with logo use, brand colours, text legibility and contrast, layout, imagery and accessibility. "
            "For each: category (Logo|Colour|Text in image|Contrast|Accessibility|Layout|Imagery), severity, rule_code (ONLY a code "
            "from the list below, else null), a short message, a short suggestion, and box = [x, y, width, height] as fractions of "
            "the image (0-1) around the problem, or null. Also copy the visible text exactly into text_in_image (empty if none). "
            "If nothing is wrong return an empty issues list. Never invent rule codes, numbers, claims or facts.\n"
            'Return JSON {"issues":[{"category","severity","rule_code","message","suggestion","box"}],"text_in_image":str}\n'
            "APPROVED RULES:\n" + gemini_service.untrusted("\n".join(f"{r['code']}: {r['text']}" for r in rules) or "(none)"),
            vs.VisionResult, temperature=0.2, image=image, _caller=_caller)
    issues = []
    for it in res.issues:
        d = it.model_dump()
        d["box"] = clean_box(d["box"]) if d["box"] else None
        r = codes.get(d["rule_code"])
        d["rule_code"] = r["code"] if r else None
        d["rule_text"] = r["text"] if r else ""
        d["source"] = (f"{r['code']} · {r['text']}" if r else "No brand rule cited — an observation, not a rule violation")
        issues.append(d)
    text = " ".join(res.text_in_image.split())
    text_audit = None
    if text:   # the facts in the picture are judged by BrandCanon's own checker, against approved facts
        text_audit = content_audit.run(ws, text, channel, "Image text", product, use_ai=False)
    return {"issues": issues, "text_in_image": text, "text_audit": text_audit, "engine": gemini_service.label_for(sources)}


def annotate(data, issues):
    """The picture with each located issue boxed and numbered (numbers match the list shown beside it)."""
    im = visual_audit.load(data)
    draw = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    t = max(3, round(min(W, H) / 220))
    try:
        font = ImageFont.load_default(size=max(14, round(min(W, H) / 38)))
    except TypeError:
        font = ImageFont.load_default()
    for i, it in enumerate(issues, 1):
        if not it.get("box"):
            continue
        x, y, w, h = it["box"]
        col = SEV_COLOUR[it["severity"]]
        x0, y0, x1, y1 = x * W, y * H, (x + w) * W, (y + h) * H
        draw.rectangle([x0, y0, x1, y1], outline=col + (255,), width=t, fill=col + (28,))
        r = max(11, round(min(W, H) / 40))
        draw.ellipse([x0 - 2, y0 - 2, x0 - 2 + 2 * r, y0 - 2 + 2 * r], fill=col + (255,))
        draw.text((x0 - 2 + r, y0 - 2 + r), str(i), fill=(255, 255, 255, 255), font=font, anchor="mm")
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def summarise(det, ai):
    """Counts by severity across deterministic findings and Gemini issues (for the campaign table)."""
    c = {"high": 0, "medium": 0, "low": 0}
    for sev, _ in det["findings"]:
        c[sev] += 1
    for it in (ai or {}).get("issues", []):
        c[it["severity"]] += 1
    if ai and ai.get("text_audit"):
        for f in ai["text_audit"]["findings"]:
            if f["classification"] != "Verified" and f["severity"] in c:
                c[f["severity"]] += 1
    return c
