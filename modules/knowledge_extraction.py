"""Extract candidate rules, product facts and terminology from stored passages.

Two engines:
* Deterministic (always available): sentence-level patterns for directives, 'Attribute: value' specs, quoted terms.
* Gemini (if configured): structured extraction validated by Pydantic. Every AI-extracted item must match a stored
  passage, otherwise it is discarded — the model cannot invent rules or facts.
Everything extracted starts as 'Pending Validation'; nothing becomes official without a human.
"""
import re

from modules import text_features as tf
from services import gemini_service, validation_service as vs

DIRECTIVE = re.compile(r"\b(must|should|always|never|avoid|do not|don't|use|maintain|keep|ensure|required?|requires|"
                       r"prohibited|only|may not|make|write|include|end with|state)\b", re.I)
CATEGORY_RULES = [
    ("Terminology", ["the word", "the term", "write \"", "in full", "instead of", "do not use \"", "never use the"]),
    ("Prohibited claims", ["superlative", "comparative", "guarantee", "evidence", "qualifier", "performance figure", "claim"]),
    ("Accessibility requirements", ["contrast", "alternative text", "alt text", "accessib", "font size"]),
    ("Visual identity", ["colour", "color", "logo", "font", "typography", "#"]),
    ("Campaign instructions", ["discount", "offer", "promotion", "end date", "campaign brief"]),
    ("Messaging", ["positioned", "positioning", "audience", "next step", "caption"]),
    ("Brand personality", ["personality", "we are", "who we are"]),
    ("Brand tone", ["tone", "voice", "friendly", "professional", "formal", "casual", "language", "exciting",
                    "persuasive", "emoji", "concise", "aggressive", "modern", "pressure"]),
]
TONE_CATEGORIES = ("Brand tone", "Brand personality", "Prohibited claims", "Campaign instructions", "Other policies")
NUM_WORDS = {"zero": 0, "no": 0, "one": 1, "a single": 1, "two": 2, "three": 3, "four": 4, "five": 5}
PRODUCT_HEADING = re.compile(r"^(.+?)\s*\((?:laptop|smartphone|phone|tablet|product|model|device|watch|earbuds|[a-z ]+)\)")
MODEL_TOKEN = re.compile(r"\b([A-Z][A-Za-z]+ [A-Z]+\d+\w*)\b")


def _num(s):
    s = s.lower()
    return float(s) if re.match(r"\d", s) else NUM_WORDS.get(s)


def parse_constraints(text: str) -> dict:
    """Turn the measurable parts of a rule into machine-checkable constraints."""
    t = text.lower()
    c = {}
    m = re.search(r"(?:no more than|at most|max(?:imum)?|up to|fewer than)\s+(\w+)\s+emojis?", t)
    if m and _num(m.group(1)) is not None:
        c["max_emoji"] = _num(m.group(1)) - (1 if "fewer than" in m.group(0) else 0)
    if re.search(r"\bno emojis?\b|without emojis?|avoid emojis?", t):
        c["max_emoji"] = 0
    if re.search(r"plenty of emojis|use emojis", t):
        c["emoji_encouraged"] = True
    m = re.search(r"(?:no more than|at most|max(?:imum)?)\s+(\w+)\s+exclamation", t)
    if m and _num(m.group(1)) is not None:
        c["max_exclaim"] = _num(m.group(1))
    if re.search(r"(no|avoid|without|never use)\s+(\w+\s+)?slang", t):
        c["no_slang"] = True
    if re.search(r"(no|avoid|without|never use|do not use)\s+(\w+\s+)?pressure", t) or "regret it" in t:
        c["no_pressure"] = True
    if re.search(r"(no|avoid)\s+(unsupported\s+)?superlatives", t):
        c["no_superlatives"] = True
    if re.search(r"(no|avoid)\s+(absolute|unsupported)\s+(promises|promotional)", t):
        c["no_absolute_promises"] = True
    if re.search(r"conversational|casual", t):
        c["informal_ok"] = True
    if "formal register" in t:
        c["formal_required"] = True
    if re.search(r"(no|avoid)\s+(overly\s+)?formal|stiff", t):
        c["no_stiff_formal"] = True
    if "benefit-led" in t or "neutral, benefit" in t:
        c["energy_optional"] = True
    m = re.search(r"sentences? (?:under|below|of at most|no longer than)\s+(\d+)\s+words", t)
    if m:
        c["max_sentence_words"] = int(m.group(1))
    m = re.search(r"(?:under|below|at most|no more than)\s+(\d+)\s+words", t)
    if m and "sentence" not in t[max(0, m.start() - 12):m.start()]:
        c.setdefault("max_words", int(m.group(1)))
    m = re.search(r"contrast ratio of at least\s+([\d.]+)\s*:\s*1", t)
    if m:
        c["min_contrast"] = float(m.group(1))
    hexes = re.findall(r"([A-Z][\w ]{1,20}?)\s+(#[0-9A-Fa-f]{6})", text)
    if hexes:
        c["palette"] = {name.strip(): h.upper() for name, h in hexes}
    if "superlative" in t or "comparative" in t:
        q = re.findall(r"[\"“]([^\"”]{2,40})[\"”]", text)
        c["evidence_terms"] = q or ["best", "most powerful", "fastest"]
    if re.search(r"alternative text|alt text", t):
        c["require_alt_text"] = True
    if "qualifier" in t:
        c["require_qualifier"] = True
    if "end date" in t:
        c["offer_end_date"] = True
    m = re.search(r"positioned for (.+?)(?:\.|$)", t)
    if m:
        hits = sorted((mm.start(), v) for k, v in tf.AUDIENCES.items() for mm in [re.search(r"\b" + k + r"\b", m.group(1))] if mm)
        c["audience"] = list(dict.fromkeys(v for _, v in hits))
    if "end with a clear next step" in t:
        c["next_step"] = True
    return c


def categorize(text):
    t = text.lower()
    for cat, kws in CATEGORY_RULES:
        if any(k in t for k in kws):
            return cat
    return "Other policies"


def scope_of(text):
    ch = tf.channels_in(text)
    return ", ".join(ch) if ch else "All content"


def qualifier_of(s):
    low = s.lower()
    parts = []
    for pat in (r"\bup to\b", r"\bapproximately\b", r"\babout\b", r"\baround\b", r"\bat least\b",
                r"under [^.,;()]*conditions", r"\btypical use\b", r"\blimited\b", r"may vary"):
        m = re.search(pat, low)
        if m:
            parts.append(m.group(0))
    return "; ".join(parts)


def deterministic(passages, default_product=None):
    """passages: list of dicts with keys idx, location, text, heading. Returns (rules, facts, terms) with passage idx."""
    rules, facts, terms = [], [], []
    last_preferred = None
    for p in passages:
        s = p["text"]
        product = p.get("product") or default_product or "General"
        m = re.match(r"^([A-Z][A-Za-z /-]{2,30}):\s*(.+)$", s)
        nus = tf.num_units(s)
        has_hex = bool(re.search(r"#[0-9A-Fa-f]{6}\b", s))
        if m and nus and not DIRECTIVE.search(m.group(1)) and not has_hex:
            pref = [n for n in nus if n[1] in ("hours", "days", "minutes")] or nus
            facts.append({"idx": p["idx"], "product": product, "attribute": m.group(1).strip().lower(),
                          "value": pref[0][0], "unit": pref[0][1], "qualifier": qualifier_of(s), "text": s})
            continue
        if m and not nus and not DIRECTIVE.search(s) and len(s) < 90 and not has_hex:
            continue  # descriptive spec line without a number (e.g. "Processor: NovaCore")
        personality = bool(re.search(r"\bpersonality is\b", s, re.I))
        if not (DIRECTIVE.search(s) or has_hex or personality or re.search(r"\bpositioned for\b", s, re.I)):
            continue
        rules.append({"idx": p["idx"], "text": s, "category": categorize(s), "scope": scope_of(s)})
        low = s.lower()
        quoted = re.findall(r"[\"“]([^\"”]{2,40})[\"”]", s)
        if quoted and "superlative" not in low and "comparative" not in low:
            if re.search(r"\binstead of\b", low) and len(quoted) >= 2:
                terms.append({"idx": p["idx"], "term": quoted[1], "kind": "prohibited", "replacement": quoted[0]})
                terms.append({"idx": p["idx"], "term": quoted[0], "kind": "preferred", "replacement": ""})
            elif re.search(r"\b(never|do not|don't|avoid|not)\b", low):
                for q in quoted:
                    terms.append({"idx": p["idx"], "term": q, "kind": "prohibited", "replacement": last_preferred or ""})
            elif re.search(r"\b(always|write|use)\b", low):
                last_preferred = quoted[0]
                terms.append({"idx": p["idx"], "term": quoted[0], "kind": "preferred", "replacement": ""})
    return rules, facts, terms


def _match_passage(text, passages):
    """Map an AI-extracted sentence to the stored passage it came from; None if it doesn't exist."""
    t = " ".join(text.lower().split())
    for p in passages:
        pt = " ".join(p["text"].lower().split())
        if t == pt or (len(t) > 15 and (t in pt or pt in t)):
            return p["idx"]
    return None


def with_gemini(passages, default_product=None):
    """Return (rules, facts, terms), or None if Gemini found nothing it could match to stored passages.

    Raises gemini_service.GeminiError if a call fails. Items whose text is not in the document are dropped, so the
    model cannot invent rules, facts or page numbers.
    """
    by_loc = {}
    for p in passages:
        by_loc.setdefault(p["location"], []).append(p)
    rules, facts, terms = [], [], []
    for loc, ps in by_loc.items():
        page = "\n".join(p["text"] for p in ps)
        res = gemini_service.generate(
            "Extract brand-governance knowledge from this page of a company document.\n"
            "rules = instructions people must follow, copied VERBATIM as one sentence each.\n"
            "facts = numeric product specifications only. terms = banned or preferred words.\n"
            f"Categories: {', '.join(vs.Category.__args__)}. Default product if unclear: {default_product or 'General'}.\n"
            'Return JSON {"rules":[{"text","category","scope"}],"facts":[{"product","attribute","value","unit","qualifier","text"}],'
            '"terms":[{"term","kind","replacement"}]}\n' + gemini_service.untrusted(page), vs.Extraction)
        for r in res.rules:
            i = _match_passage(r.text, ps)
            if i is not None:
                rules.append({"idx": i, "text": r.text, "category": r.category, "scope": r.scope or scope_of(r.text)})
        for f in res.facts:
            i = _match_passage(f.text, ps)
            if i is not None:
                facts.append({"idx": i, "product": f.product, "attribute": f.attribute.lower(), "value": f.value,
                              "unit": tf.norm_unit(f.unit), "qualifier": f.qualifier or qualifier_of(f.text), "text": f.text})
        for t in res.terms:
            src = next((p for p in ps if t.term.lower() in p["text"].lower()), None)
            if src:
                terms.append({"idx": src["idx"], "term": t.term, "kind": t.kind, "replacement": t.replacement})
    return (rules, facts, terms) if (rules or facts) else None


def prepare_passages(pages):
    """pages -> passage dicts (one per sentence) carrying the current product heading."""
    title = pages[0][1].strip().splitlines()[0] if pages and pages[0][1].strip() else ""
    m = MODEL_TOKEN.search(title)
    default_product = m.group(1) if m else None
    out, product = [], None
    from modules.document_parser import split_sentences
    for loc, text in pages:
        for kind, s in split_sentences(text):
            if kind == "H":
                hm = PRODUCT_HEADING.match(s)
                if hm:
                    product = hm.group(1).strip()
                continue
            if len(s) >= 4:
                out.append({"idx": len(out), "location": loc, "text": s, "product": product})
    return out, default_product


def extract(pages, use_ai=True):
    """Returns (passages, rules, facts, terms, engine_label, ai_error_message_or_None)."""
    passages, default_product = prepare_passages(pages)
    res, ai_error = None, None
    engine = gemini_service.fallback_label() if use_ai else gemini_service.deterministic_label()
    if use_ai and gemini_service.enabled():
        with gemini_service.tracking() as sources:
            try:
                res = with_gemini(passages, default_product)
                engine = (gemini_service.label_for(sources) if res else
                          f"{gemini_service.DETERMINISTIC} (Gemini found no rules or facts that match the document text)")
            except gemini_service.GeminiError as e:
                ai_error, engine = e.message, gemini_service.fallback_label(e)
    elif use_ai and gemini_service.requested():
        ai_error = gemini_service.not_available_error().message
    rules, facts, terms = res or deterministic(passages, default_product)
    return passages, rules, facts, terms, engine, ai_error
