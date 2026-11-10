"""Content Intelligence: audit text against validated brand knowledge.

Order of checks (deterministic first, AI last):
  1. Terminology (exact matching)            → Violation
  2. Product facts & qualifiers (structured)  → Contradicted / Unsupported / Verified
  3. Superlatives & absolute promises         → Unverifiable / Unsupported (never "false" without evidence)
  4. Tone (rule constraints; strict vs lenient when a rule is still ambiguous)
  5. Messaging, channel & accessibility rules
  6. Gemini contextual pass (optional, validated, additive, labelled)
Every finding cites a stored rule/fact/passage or says plainly that no evidence was found.
"""
import re

from database import repositories as repo
from modules import ambiguity_detection as amb
from modules import conflict_detection, evidence_retrieval as er
from modules import text_features as tf
from services import gemini_service, validation_service as vs

SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
HYPE = {"revolutionary", "game-changing", "game changing", "perfect", "ultimate"}
DEFAULT_REPLACE = {"unbreakable": "durable", "risk-free": "", "guaranteed results": ""}
CTA = re.compile(r"\b(explore|learn more|visit|shop|discover|find out|link in bio|see how|try|order|book|sign up|read more)\b", re.I)
DATE = re.compile(r"\b(\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*|"
                  r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}|\d{1,2}/\d{1,2}|until|ends on|valid till|till)\b", re.I)
LIVE_RULES = ("Approved", "Pending Validation", "Needs Clarification")
LIVE_FACTS = ("Approved", "Pending Validation")


def _rule_ev(rule):
    if not rule:
        return {}
    return {"rule_id": rule["id"], "passage_id": rule.get("passage_id"),
            "evidence_text": rule.get("source_text") or rule["text"],
            "evidence_source": f"{rule['code']} v{rule['rule_version']} · " + er.cite(rule),
            "rule_status": rule["status"]}


def _fact_ev(f):
    return {"fact_id": f["id"], "passage_id": f.get("passage_id"), "evidence_text": f.get("source_text") or f["raw_text"],
            "evidence_source": er.cite(f) + f" · {f['authority_level']}"}


def _expand(text, s, e, left_words=("guaranteed", "a", "full", "the", "just", "only", "an", "all-day"),
            right_keep=None):
    while True:
        m = re.search(r"(\b\w[\w-]*)\s+$", text[:s])
        if m and m.group(1).lower() in left_words:
            s = m.start(1)
        else:
            break
    if right_keep:
        m = re.match(r"((?:\s*-?\s*(?:of\s+)?(?:uninterrupted\s+)?(?:" + "|".join(map(re.escape, right_keep)) + r")\b)+)", text[e:], re.I)
        if m:
            e += len(m.group(1))
    return s, e


def _fact_suggestion(f):
    t = (f.get("raw_text") or "").lower()
    qual = " under specified testing conditions" if ("testing conditions" in t or "specified" in t) else ""
    if "up to" in (f["qualifier"] or "") or "up to" in t:
        if "typical use" in t:
            return f"up to {f['value']:g} {f['unit']} of {f['attribute']} with typical use"
        return f"up to {f['value']:g} {f['unit']} of {f['attribute']}{qual}"
    return f"{f['value']:g} {f['unit']}"


def _verified_alternative(span, facts, mentioned):
    pool = [f for f in facts if f["product"] in mentioned]
    low = span.lower()
    f = next((f for f in pool if any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in f["attribute"].split() if len(w) > 3)), None)
    f = f or next((f for f in pool if f["unit"] == "GHz"), None)
    if f is None:
        return "a specific, verified product benefit"
    if f["unit"] == "GHz":
        raw = re.sub(r"^[^:]+:\s*", "", f["raw_text"]).rstrip(".")
        name, _, rest = raw.partition(",")
        noun = "a laptop" if ("laptop" in low or "machine" in low) else "a device"
        return f"{noun} with a {name.strip()} processor ({rest.strip()})" if rest else f"{noun} with a {raw} processor"
    return f"a {f['value']:g} {f['unit']} {f['attribute']}"


def _neutral(fix, product):
    w = tf.words(fix)
    if len(w) < 4 or re.search(r"\b(is|are|so|very|really|the|a)\s*[.!?]?$", fix.strip()):
        return f"Meet {product}." if product else "Meet our latest product."
    return fix


def run(ws, text, channel="Instagram", content_type="Social media caption", product=None, has_image=False,
        alt_text="", use_ai=True):
    """Audit text. Returns {'findings': [...], 'status', 'counts', 'engine', 'product'} (not yet persisted)."""
    text = text or ""
    rules = [r for r in repo.list_rules(ws, LIVE_RULES) if conflict_detection.scopes_overlap(r["scope"], channel)]
    facts_all = repo.list_facts(ws)
    facts = [f for f in facts_all if f["status"] in LIVE_FACTS]
    prods = sorted({f["product"] for f in facts_all})
    mentioned = [p for p in prods if p.lower() in text.lower()] or ([product] if product else [])
    if mentioned and product not in mentioned:
        product = mentioned[0]  # the text names a product explicitly: trust it over the dropdown
    findings = []

    def add(**kw):
        kw.setdefault("confidence", "high")
        kw.setdefault("engine", "Deterministic")
        kw.setdefault("suggestion", "")
        kw["quote"] = text[kw["span_start"]:kw["span_end"]] if kw.get("span_end") else ""
        findings.append(kw)

    def overlaps(s, e):
        return any(f.get("span_end") and not (e <= f["span_start"] or s >= f["span_end"]) for f in findings)

    # 1 ---- terminology
    rule_by_id = {r["id"]: r for r in repo.list_rules(ws)}
    for t in repo.list_terms(ws, "prohibited"):
        for m in re.finditer(r"(?<![\w])" + re.escape(t["term"]) + r"(?![\w])", text, re.I):
            rep = t["replacement"] or DEFAULT_REPLACE.get(t["term"].lower(), "")
            add(category="Terminology", classification="Violation", severity="high", span_start=m.start(), span_end=m.end(),
                message=f"\"{m.group(0)}\" is on the prohibited term list." + (f" Use \"{rep}\" instead." if rep else " Remove or rephrase it."),
                suggestion=rep, root_cause="Creator error", **_rule_ev(rule_by_id.get(t["rule_id"])))

    # 2 ---- product facts & qualifiers
    qual_rule = next((r for r in rules if r["constraints"].get("require_qualifier")), None)
    CONV = {"TB": ("GB", 1000), "g": ("kg", 0.001)}
    for val0, unit0, s, e in tf.num_units(text):
        unit, mult = CONV.get(unit0, (unit0, 1))
        val = val0 * mult
        if not any(f["unit"] == unit and f["product"] in mentioned for f in facts):
            unit, val = unit0, val0
        cands = [f for f in facts_all if f["unit"] == unit and f["product"] in mentioned and f["status"] not in ("Rejected", "Archived")]
        live = [f for f in cands if f["status"] in LIVE_FACTS]
        if not live:
            continue
        sent = next((x for x in tf.sentences(text) if x[0] <= s < x[1]), (s, e, ""))
        window = text[max(sent[0], s - 40):min(sent[1], e + 40)].lower()
        right, left = text[e:e + 28].lower(), text[max(0, s - 28):s].lower()

        def near(attr):
            ws_ = [w for w in attr.split() if len(w) > 2]
            sc = 3 * any(w in right for w in ws_) + 2 * any(w in left for w in ws_) + any(w in window for w in ws_)
            return sc + (3.5 if any(abs(x["value"] - val) < 1e-9 for x in live if x["attribute"] == attr) else 0)
        attr = max({x["attribute"] for x in live}, key=near)
        group = [x for x in live if x["attribute"] == attr]
        top = max(group, key=lambda x: (x["status"] == "Approved", x["authority_rank"] or 0))
        attr_words = [w for w in attr.split() if len(w) > 2] + [attr, "battery life", "battery", "life"]
        ss, ee = _expand(text, s, e, right_keep=attr_words)
        if overlaps(ss, ee):
            continue
        absolute = [a for a in tf.ABSOLUTE if re.search(r"\b" + re.escape(a) + r"\b", window)]
        has_upto = bool(re.search(r"up to\s*$", text[max(0, ss - 8):ss].lower()))
        conflict_open = any(repo.open_conflicts_for_fact(x["id"]) for x in group)
        stale = next((x for x in cands if x["id"] != top["id"] and abs(x["value"] - val) < 1e-9), None)
        if abs(val - top["value"]) > 1e-9:
            msg = f"Says {val0:g} {unit0}, but {top['doc_title']} states {top['value']:g} {top['unit']}" + \
                  (f" ({top['qualifier']})." if top["qualifier"] else ".")
            if stale:
                msg += f" The {val0:g} {unit0} figure appears in {stale['doc_title']} (v{stale['doc_version']}, {stale['authority_level']})."
            if conflict_open:
                msg += " The sources still disagree — the conflict has not been resolved yet."
            add(category="Product facts", classification="Contradicted", severity="high", span_start=ss, span_end=ee,
                message=msg, suggestion=_fact_suggestion(top), root_cause="Source conflict" if (stale or conflict_open) else "Creator error",
                confidence="medium" if conflict_open else "high", **_fact_ev(top))
        elif absolute and top["qualifier"]:
            add(category="Product facts", classification="Unsupported", severity="high", span_start=ss, span_end=ee,
                message=f"Turns a qualified specification (\"{top['qualifier']}\") into an absolute promise (\"{absolute[0]}\").",
                suggestion=_fact_suggestion(top), root_cause="Creator error", **_fact_ev(top))
        elif top["qualifier"] and "up to" in top["qualifier"] and not has_upto:
            ev = _rule_ev(qual_rule) if qual_rule else _fact_ev(top)
            add(category="Product facts", classification="Unsupported", severity="medium", span_start=ss, span_end=ee,
                message=f"Uses the specification figure without its qualifier (\"{top['qualifier']}\").",
                suggestion=_fact_suggestion(top), root_cause="Creator error", **ev)
        else:
            add(category="Product facts", classification="Verified", severity="info", span_start=ss, span_end=ee,
                message=f"Matches {top['doc_title']} ({top['value']:g} {top['unit']}).", root_cause="Not applicable", **_fact_ev(top))

    # 3 ---- guarantees, superlatives & absolute promises
    ev_rule = next((r for r in rules if r["constraints"].get("evidence_terms")), None)
    promise_rule = next((r for r in rules if "promis" in r["text"].lower() and "absolute" in r["text"].lower()), None)
    for m in re.finditer(r"\bguarantee(s)?\b", text, re.I):
        if overlaps(m.start(), m.end()):
            continue
        ev = _rule_ev(promise_rule) if promise_rule else {"evidence_text": "", "evidence_source": "No approved evidence found"}
        add(category="Claims", classification="Unsupported", severity="high", span_start=m.start(), span_end=m.end(),
            message="Unsupported guarantee: approved sources describe what the product offers under stated conditions; "
                    "none of them guarantees an outcome.",
            suggestion="offers" if m.group(1) else "offer", root_cause="Creator error" if promise_rule else "Knowledge gap", **ev)
    for s, e, hit in tf.find_phrases(text, tf.SUPERLATIVE):
        if overlaps(s, e):
            continue
        ss, ee = _expand(text, s, e, left_words=("the", "our", "a"))
        m = re.match(r"((?:\s+[a-z-]+){0,2}?\s+(?:laptop|phone|smartphone|device|product|camera|display|machine|battery|screen)s?)?"
                     r"(\s+ever made|\s+in (?:its|the) class|\s+in the world|\s+on the market)?", text[ee:], re.I)
        if m:
            ee += len(m.group(0))
        rule_like = re.compile(r"\b(claims?|evidence|require[sd]?|must|never|do not|avoid|such as|pitch)\b", re.I)
        support = [p for p in er.search(ws, text[ss:ee], k=5) if hit.lower() in p["text"].lower()]
        strong = [p for p in support if (p["authority_rank"] or 0) >= 3 and not rule_like.search(p["text"])]
        support = [p for p in support if not rule_like.search(p["text"]) or (p["authority_rank"] or 0) < 3]
        if strong:
            p = strong[0]
            add(category="Claims", classification="Verified", severity="info", span_start=ss, span_end=ee,
                message=f"Supported by {p['doc_title']}.", root_cause="Not applicable", passage_id=p["id"],
                evidence_text=p["text"], evidence_source=er.cite(p))
            continue
        hype = hit.lower() in HYPE
        before_product = any(text[ee:].lstrip().lower().startswith(p.lower()) for p in mentioned if p)
        msg = (f"\"{hit}\" is a hype claim with no approved evidence. Prefer a concrete, verifiable benefit." if hype else
               "Superlative or comparative claim with no approved evidence. Classified as unverifiable, not false.")
        if support and not hype:
            msg += f" It appears only in {support[0]['doc_title']} ({support[0]['authority_level']}), which is not evidence."
        ev = _rule_ev(ev_rule) if ev_rule else {"evidence_text": "", "evidence_source": "No approved evidence or claims policy found"}
        add(category="Claims", classification="Unverifiable", severity="medium" if hype else ("high" if ev_rule else "medium"),
            span_start=ss, span_end=ee, message=msg,
            suggestion="the new" if (hype and before_product) else _verified_alternative(text[ss:ee], facts, mentioned),
            root_cause="Creator error" if ev_rule else "Knowledge gap", confidence="high" if ev_rule else "medium", **ev)
    for s, e, hit in tf.find_phrases(text, tf.PROMISE):
        sent = next((x for x in tf.sentences(text) if x[0] <= s < x[1]), None)
        if not sent:
            continue
        ss = max(sent[0], s - 0)
        m = re.search(r"\b(will|can|to)\s+$", text[sent[0]:s])
        if m:
            ss = sent[0] + m.start()
        ee = sent[1] - (1 if text[sent[1] - 1:sent[1]] in ".!?" else 0)
        if overlaps(ss, ee):
            continue
        ev = _rule_ev(promise_rule) if promise_rule else {"evidence_text": "", "evidence_source": "No approved evidence found"}
        tail = re.search(r"(your [\w\s]+?)(?:\s+forever)?[.!?]?$", text[ss:ee + 1])
        benefit = tail.group(1).strip() if tail else "your work"
        add(category="Claims", classification="Unsupported", severity="medium", span_start=ss, span_end=ee,
            message="Absolute promotional promise with no approved evidence to substantiate it.",
            suggestion=f"can support {benefit}" if text[ss:ss + 4].lower() == "will" else f"support {benefit}",
            root_cause="Creator error" if promise_rule else "Knowledge gap", **ev)

    # 4 ---- tone (constraints, or strict-vs-lenient while a rule is still ambiguous)
    seen = {}
    for r in rules:
        cons = r["constraints"]
        for d, direction in amb.rule_dims(r).items():
            if direction != "away" or d == "superlative":
                continue
            smax, lmax, defined = amb.thresholds(d, direction, cons)
            for s, e, sent in tf.sentences(text):
                lvl = amb.level(d, sent)
                if d == "length":
                    lim = cons.get("max_sentence_words")
                    if not lim or tf.features(sent)["max_sentence_words"] < lim:
                        continue
                    strict_fail = lenient_fail = True
                elif d == "emoji" and "max_emoji" in cons:
                    strict_fail = lenient_fail = tf.features(text)["emoji"] > cons["max_emoji"]
                else:
                    strict_fail = lvl > (smax if isinstance(smax, (int, float)) else 99)
                    lenient_fail = lvl > (lmax if isinstance(lmax, (int, float)) else 99)
                if not strict_fail or (s, d) in seen or overlaps(s, e):
                    continue
                ambiguous = not lenient_fail
                fix = ""
                if d == "pressure":
                    fix = f"Explore how {product or 'it'} can support your everyday work."
                elif d == "informality":
                    fix = re.sub(r"\b(\w*?)([a-z])\2{2,}(\w*)\b", r"\1\2\3", sent)
                    for sl in tf.SLANG:
                        fix = re.sub(r"\b" + sl + r"\b\s*", "", fix, flags=re.I)
                    fix = _neutral(re.sub(r"\s+([,.!?])", r"\1", re.sub(r"!+", ".", fix)).strip(" ,"), product)
                elif d == "energy":
                    fix = re.sub(r"\b([A-Z]{4,})\b", lambda m: m.group(1).capitalize(), re.sub(r"!+", ".", sent))
                elif d == "emoji":
                    first = tf.EMOJI.search(sent)
                    fix = tf.EMOJI.sub("", sent).rstrip() + (" " + first.group(0) if first and cons.get("max_emoji", 0) >= 1 else "")
                elif d == "formality":
                    fix = f"We're excited to introduce {product or 'our latest product'}."
                add(category="Tone", classification="Needs review" if ambiguous else "Violation",
                    severity="low" if ambiguous else "medium", span_start=s, span_end=e,
                    message=(f"{amb.DIMS[d]['label']} may break {r['code']} under a strict reading but not a lenient one. "
                             f"The rule does not define this boundary yet, so a human should decide (see RuleProbe)."
                             if ambiguous else f"{amb.DIMS[d]['label']} goes beyond what {r['code']} v{r['rule_version']} allows."),
                    suggestion=fix, root_cause="Guideline defect" if ambiguous else "Creator error",
                    confidence="low" if ambiguous else "high", **_rule_ev(r))
                seen[(s, d)] = True

    # 5 ---- messaging, channel, accessibility
    for r in rules:
        aud = r["constraints"].get("audience")
        if not aud or (mentioned and not any(p.lower() in r["text"].lower() for p in mentioned)):
            continue
        for k, v in tf.AUDIENCES.items():
            for m in re.finditer(r"\b" + re.escape(k) + r"\b", text, re.I):
                if v in aud:
                    continue
                s, e = _expand(text, m.start(), m.end(), left_words=("professional", "pro", "hardcore", "serious", "for"))
                if overlaps(s, e):
                    continue
                add(category="Messaging", classification="Violation", severity="medium", span_start=s, span_end=e,
                    message=f"Targets {v}, but the approved positioning is for {', '.join(aud)}.",
                    suggestion="for " + " and ".join(aud) if text[s:e].lower().startswith("for") else " and ".join(aud),
                    root_cause="Creator error", **_rule_ev(r))
    feats = tf.features(text)
    for r in rules:
        c = r["constraints"]
        scoped = channel.lower() in (r["scope"] or "").lower() or (r["scope"] == "Instagram" and channel == "Instagram")
        if c.get("max_words") and scoped and feats["words"] > c["max_words"]:
            add(category="Messaging", classification="Violation", severity="low", span_start=None, span_end=None,
                message=f"{feats['words']} words; {r['code']} asks for under {c['max_words']} on {channel}.", root_cause="Creator error", **_rule_ev(r))
        if c.get("next_step") and scoped and not CTA.search(text):
            add(category="Messaging", classification="Violation", severity="low", span_start=None, span_end=None,
                message=f"No clear next step at the end ({r['code']}).", suggestion="", root_cause="Creator error", **_rule_ev(r))
        if c.get("offer_end_date") and re.search(r"\b(offer|discount|% off|sale|deal)\b", text, re.I) and not DATE.search(text):
            add(category="Campaign", classification="Violation", severity="medium", span_start=None, span_end=None,
                message=f"Offer mentioned without an end date ({r['code']}).", root_cause="Creator error", **_rule_ev(r))
        if c.get("require_alt_text") and has_image and not (alt_text or "").strip():
            add(category="Accessibility", classification="Violation", severity="medium", span_start=None, span_end=None,
                message=f"The image has no alternative text ({r['code']}).", root_cause="Creator error", **_rule_ev(r))

    # 6 ---- Gemini contextual pass (additive; validated; labelled). Failures are reported, never hidden.
    engine = gemini_service.fallback_label() if use_ai else gemini_service.deterministic_label()
    ai_error = None
    if use_ai and gemini_service.enabled() and text.strip():
        ev = er.search(ws, text, k=6)
        approved = [r for r in rules if r["status"] == "Approved"][:40]
        with gemini_service.tracking() as sources:
            try:
                res = gemini_service.generate(
                    "Audit the marketing CONTENT against the company's APPROVED RULES and EVIDENCE only.\n"
                    f"Channel: {channel}. Content type: {content_type}. Product: {product}.\n"
                    "Find tone, messaging/positioning or unsupported-claim problems that are NOT about exact numbers or banned words.\n"
                    "Each quote must be an exact substring of the content. Each suggestion must be a replacement for the quote "
                    "that keeps the message and adds no new facts, numbers or claims. If nothing is wrong return an empty list.\n"
                    'Return JSON {"findings":[{"quote","category":"Tone|Messaging|Unsupported claim","severity":"high|medium|low",'
                    '"rule_code","message","suggestion"}]}\n'
                    "APPROVED RULES:\n" + gemini_service.untrusted("\n".join(f"{r['code']}: {r['text']}" for r in approved)) +
                    "\nEVIDENCE:\n" + gemini_service.untrusted("\n".join(f"[{er.cite(p)}] {p['text']}" for p in ev)) +
                    "\nCONTENT:\n" + gemini_service.untrusted(text), vs.AIFindings)
            except gemini_service.GeminiError as e:
                res, ai_error, engine = None, e.message, gemini_service.fallback_label(e)
        if res is not None:
            live = gemini_service.label_for(sources)
            engine = live + " + deterministic checks"
            by_code = {r["code"]: r for r in rules}
            for g in res.findings:
                pos = text.find(g.quote)
                if pos < 0 or overlaps(pos, pos + len(g.quote)):
                    continue  # quotes that are not in the content are discarded
                r = by_code.get(g.rule_code)
                sug = g.suggestion if _grounded(g.suggestion, text, ws) else ""
                cat = {"Tone": "Tone", "Messaging": "Messaging", "Unsupported claim": "Claims"}[g.category]
                add(category=cat, classification="Unsupported" if cat == "Claims" else "Violation", severity=g.severity,
                    span_start=pos, span_end=pos + len(g.quote), message=g.message, suggestion=sug,
                    root_cause="Creator error" if r else "Unresolved / other", confidence="medium", engine=live,
                    **(_rule_ev(r) if r else {"evidence_text": "", "evidence_source": "AI judgement — no specific rule cited"}))
    elif use_ai and gemini_service.requested():
        ai_error = gemini_service.not_available_error().message

    for f in findings:
        if f.get("rule_status") in ("Pending Validation", "Needs Clarification"):
            f["message"] += f" (Based on a rule with status: {f['rule_status']}.)"
            if f["confidence"] == "high":
                f["confidence"] = "medium"
    findings.sort(key=lambda f: (SEV_ORDER[f["severity"]], f.get("span_start") if f.get("span_start") is not None else 10**6))
    issues = [f for f in findings if f["classification"] != "Verified"]
    counts = {s: sum(1 for f in issues if f["severity"] == s) for s in ("high", "medium", "low")}
    status = "Changes needed" if counts["high"] else ("Review suggested" if issues else "No issues found")
    return {"findings": findings, "counts": counts, "status": status, "engine": engine, "product": product,
            "channel": channel, "content_type": content_type, "ai_error": ai_error}


def apply_suggestions(text, findings, replacements):
    """replacements: {finding_index: replacement_text}. Applied right-to-left so offsets stay valid."""
    chosen = sorted(((findings[i], rep) for i, rep in replacements.items()
                     if findings[i].get("span_end") and findings[i]["span_end"] > findings[i]["span_start"]),
                    key=lambda x: -x[0]["span_start"])
    used = []
    for f, rep in chosen:
        if any(not (f["span_end"] <= s or f["span_start"] >= e) for s, e in used):
            continue
        text = text[:f["span_start"]] + rep + text[f["span_end"]:]
        used.append((f["span_start"], f["span_start"] + len(rep)))
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([.,!?])", r"\1", text)
    text = re.sub(r"\.\s*\.", ".", text)
    return re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text.strip())


NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _grounded(candidate, original, ws):
    """A Gemini suggestion may only use numbers already in the content or in approved facts, and no banned terms."""
    if not candidate:
        return True
    allowed = set(NUM.findall(original))
    for f in repo.list_facts(ws, ("Approved",)):
        allowed |= set(NUM.findall(f"{f['value']:g} {f.get('qualifier') or ''} {f.get('raw_text') or ''}"))
    if set(NUM.findall(candidate)) - allowed:
        return False
    low = candidate.lower()
    return not any(re.search(r"\b" + re.escape(t["term"].lower()) + r"\b", low) for t in repo.list_terms(ws, "prohibited"))


def ai_rewrite(ws, text, findings, product=None, channel=""):
    """Gemini proposes a full corrected version. Returns {'text', 'changes', 'engine'}.

    Raises GeminiError if Gemini is off or fails, or if the rewrite introduces numbers that are not in the content or in
    approved facts, or uses a banned term. Nothing is saved: a person decides whether to use it.
    """
    if not gemini_service.enabled():
        raise gemini_service.not_available_error()
    issues = [f for f in findings if f["classification"] != "Verified" and f.get("disposition", "open") != "dismissed"]
    if not issues:
        raise ValueError("There are no open findings to correct.")
    facts = [f for f in repo.list_facts(ws, ("Approved",)) if not product or f["product"] == product]
    basis = text + " " + " ".join(f["suggestion"] or "" for f in issues)

    def check(obj):
        if not _grounded(obj.text, basis, ws):
            new = sorted(set(NUM.findall(obj.text)) - set(NUM.findall(basis)))
            raise gemini_service.GeminiError(
                "ungrounded", "Gemini's rewrite introduced " + (
                    f"numbers that are not in the content or approved facts ({', '.join(new)})" if new else "a banned term")
                + ". It was discarded.")
    with gemini_service.tracking() as sources:
        res = gemini_service.generate(
            "Rewrite the CONTENT so it fixes ONLY the listed ISSUES. Keep the message, voice, language and roughly the same "
            "length. Use only facts from APPROVED FACTS; add no new numbers, claims, prices or promises. "
            f"Channel: {channel}. Product: {product or 'not specified'}.\n"
            'Return JSON {"text": the full rewritten content, "changes": [short description of each change]}\n'
            "ISSUES:\n" + gemini_service.untrusted("\n".join(
                f"- {f['quote'] or '(whole text)'}: {f['message']}" + (f" Suggested: {f['suggestion']}" if f["suggestion"] else "")
                for f in issues)) +
            "\nAPPROVED FACTS:\n" + gemini_service.untrusted("\n".join(
                f"{f['product']} {f['attribute']}: {f['value']:g} {f['unit']} {f.get('qualifier') or ''}".strip() for f in facts)
                or "(none)") +
            "\nCONTENT:\n" + gemini_service.untrusted(text), vs.Rewrite, temperature=0.3, check=check)
    out = res.text.strip()
    return {"text": out, "changes": res.changes, "engine": gemini_service.label_for(sources)}
