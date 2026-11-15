"""Controlled-case generation and strict-vs-lenient evaluation (the measurable core of RuleProbe).

A rule is *potentially* ambiguous when reasonable strict and lenient readings disagree on realistic examples that
differ in only one characteristic. This is evidence for human review, not mathematical proof of ambiguity.
"""
import re

from modules import text_features as tf

DIMS = {
    "formality": {"label": "Formality", "cases": [
        (1, "We are pleased to inform you that {p} is now available."),
        (2, "We cordially invite you to commence utilisation of {p}, pursuant to your requirements.")],
        "clarify": "conversational language, never stiff or overly formal",
        "clarify_toward": "a formal register in complete sentences, with no slang",
        "question": "How formal may the language be?"},
    "informality": {"label": "Informality and slang", "cases": [
        (1, "Hey! Ready to explore {p}?"),
        (2, "Heyyy besties, {p} is literally insane!!!")],
        "clarify": "no slang or stretched words (for example \"heyyy\" or \"literally insane\")",
        "clarify_toward": "casual, conversational language is expected, but no slang or stretched words",
        "question": "Are casual greetings or slang acceptable?"},
    "emoji": {"label": "Emoji use", "cases": [
        (1, "Meet {p}, built for your everyday work. 🚀"),
        (2, "Meet {p} 🚀🔥😍✨💯")],
        "clarify": "at most one emoji per post",
        "clarify_toward": "emoji are optional, at most one emoji per post",
        "question": "How many emoji are acceptable?"},
    "energy": {"label": "Excitement and volume", "cases": [
        (1, "Meet {p}: big performance for your everyday work!"),
        (2, "WOW!!! {p} is HERE and it is AMAZING!!!")],
        "clarify": "at most one exclamation mark; excitement should come from concrete benefits, so a neutral, benefit-led sentence is acceptable",
        "question": "How much enthusiasm is required or allowed?"},
    "pressure": {"label": "Sales pressure", "cases": [
        (1, "Offer ends tonight, so don't miss out on {p}."),
        (2, "Purchase immediately or regret it forever.")],
        "clarify": "no pressure phrases such as \"buy now or regret it\" (a factual end date is fine)",
        "clarify_toward": "persuade through concrete benefits, with no pressure phrases such as \"buy now or regret it\"",
        "question": "Is urgency acceptable, and where does it become pressure?"},
    "superlative": {"label": "Superlatives", "cases": [
        (1, "{p} is one of our most capable laptops yet."),
        (2, "{p} is the most powerful laptop ever made.")],
        "clarify": "no superlatives such as \"best\" or \"most powerful\" without approved evidence",
        "question": "Are superlatives allowed without evidence?"},
    "length": {"label": "Sentence length", "cases": [
        (1, "With {p} you can move from lectures to meetings to late-night projects without searching for a charger, thanks to efficient components."),
        (2, "With {p} you can move from lectures to meetings to late-night projects and weekend trips without searching for a charger, because every component, from the processor to the display and the cooling system, was chosen to balance performance with efficiency for people who work everywhere.")],
        "clarify": "sentences under 25 words",
        "question": "What counts as concise?"},
}
BASELINE = "We're happy to help you get started with {p}."

# vague word -> [(dimension, direction)]; "away" = less is better, "toward" = the rule asks for this quality
TRIGGERS = {
    "friendly": [("formality", "away")], "approachable": [("formality", "away")], "warm": [("formality", "away")],
    "conversational": [("formality", "away")], "casual": [("informality", "toward"), ("formality", "away")],
    "professional": [("informality", "away")], "formal": [("formality", "toward"), ("informality", "away")],
    "modern": [("formality", "away"), ("emoji", "toward")], "fresh": [("formality", "away")],
    "exciting": [("energy", "toward")], "bold": [("energy", "toward")], "engaging": [("energy", "toward")],
    "persuasive": [("pressure", "toward")], "aggressive": [("pressure", "away"), ("superlative", "away")],
    "concise": [("length", "away")], "clear": [("length", "away")], "simple": [("length", "away")],
    "premium": [("informality", "away")], "fun": [("informality", "toward")],
}
VAGUE_WORDS = sorted(set(TRIGGERS) | {"innovative", "trustworthy", "authentic", "punchy", "engaging", "on-brand"})
TESTABLE_CATEGORIES = ("Brand tone", "Brand personality", "Prohibited claims", "Campaign instructions", "Other policies")
NEGATED = re.compile(r"\b(avoid|never|no|not|don't|do not|without)\b")


def level(dim, text):
    """Deterministic intensity (0-2) of one characteristic in a text."""
    f = tf.features(text)
    if dim == "formality":
        return min(2, len(f["formal"]))
    if dim == "informality":
        return 2 if f["slang"] else (1 if f["informal"] else 0)
    if dim == "emoji":
        return min(2, f["emoji"])
    if dim == "energy":
        return 2 if (f["exclaim"] >= 2 or f["caps"]) else (1 if f["exclaim"] == 1 else 0)
    if dim == "pressure":
        low = text.lower()
        strong = [p for p in f["pressure"] if p.lower() in ("buy now", "regret", "now or never", "act now", "hurry")] \
            or re.search(r"purchase immediately|regret it", low)
        return 2 if strong else (1 if f["pressure"] else 0)
    if dim == "superlative":
        if not f["superlative"]:
            return 0
        return 1 if re.search(r"one of (our|the) most", text.lower()) else 2
    if dim == "length":
        n = f["max_sentence_words"]
        return 0 if n <= 20 else (1 if n <= 35 else 2)
    return 0


def rule_dims(rule):
    """(dimension -> direction) the rule speaks to, from its wording and parsed constraints."""
    if rule.get("category") not in TESTABLE_CATEGORIES:
        return {}
    text = rule["text"].lower()
    cons = rule.get("constraints") or {}
    pairs = {}
    for word, dd in TRIGGERS.items():
        m = re.search(r"\b" + word + r"\b", text)
        if not m:
            continue
        neg = bool(NEGATED.search(text[max(0, m.start() - 25):m.start()]))
        for d, direction in dd:
            pairs.setdefault(d, "away" if (neg and direction == "toward") else direction)
    if "max_emoji" in cons:
        pairs["emoji"] = "away"
    if cons.get("emoji_encouraged"):
        pairs["emoji"] = "toward"
    if cons.get("no_slang"):
        pairs.setdefault("informality", "away")
    if "max_exclaim" in cons:
        pairs["energy"] = "away"
    if "max_sentence_words" in cons:
        pairs["length"] = "away"
    if cons.get("no_pressure"):
        pairs["pressure"] = "away"
    if cons.get("no_superlatives") or cons.get("evidence_terms"):
        pairs["superlative"] = "away"
    return pairs


def vague_terms(text):
    t = text.lower()
    return [w for w in VAGUE_WORDS if re.search(r"\b" + re.escape(w) + r"\b", t)]


def thresholds(dim, direction, cons):
    """(strict_limit, lenient_limit, defined). Limit = highest allowed level; 'need' = quality must be present."""
    if dim == "emoji" and "max_emoji" in cons:
        return cons["max_emoji"], cons["max_emoji"], True
    if dim == "informality" and cons.get("no_slang"):
        return 1, 1, True
    if dim == "formality" and cons.get("formal_required"):
        return "need", "need", True
    if dim == "formality" and cons.get("no_stiff_formal"):
        return 0, 0, True
    if dim == "formality" and cons.get("informal_ok") and direction == "away":
        return 1, 1, True
    if dim == "energy" and ("max_exclaim" in cons or cons.get("energy_optional")):
        m = cons.get("max_exclaim", 1)
        return m, m, True
    if dim == "pressure" and cons.get("no_pressure"):
        return 0, 0, True
    if dim == "superlative" and (cons.get("no_superlatives") or cons.get("evidence_terms")):
        return 0, 0, True
    if dim == "length" and "max_sentence_words" in cons:
        return "len", "len", True
    if direction == "away":
        return 0, 1, False
    return "need", None, False


def _verdict(text, dim, lvl, limit, cons):
    if limit is None:
        return "pass", "A broad reading accepts any level of this characteristic."
    if limit == "need":
        return (("fail", f"A narrow reading expects clear {DIMS[dim]['label'].lower()}, and this example shows none.")
                if lvl == 0 else ("pass", f"Shows the {DIMS[dim]['label'].lower()} the rule asks for."))
    if limit == "len":
        n = tf.features(text)["max_sentence_words"]
        return ("pass" if n < cons["max_sentence_words"] else "fail"), f"Longest sentence has {n} words (limit {cons['max_sentence_words']})."
    if dim == "emoji":
        n = tf.features(text)["emoji"]
        return ("pass" if n <= limit else "fail"), f"{n} emoji; this reading allows {int(limit)}."
    label = DIMS[dim]["label"].lower()
    return (("pass", f"Level {lvl} {label} is within what this reading allows.") if lvl <= limit
            else ("fail", f"Level {lvl} {label} goes beyond what this reading allows."))


def generate_cases(rule, product):
    """Baseline + two variants per dimension, each changing exactly one characteristic. Deterministic and reproducible."""
    pairs = rule_dims(rule)
    cases = [{"dimension": "baseline", "level": 0, "example": BASELINE.format(p=product)}]
    for d in pairs:
        for lvl, tpl in DIMS[d]["cases"]:
            cases.append({"dimension": d, "level": lvl, "example": tpl.format(p=product)})
    return cases, pairs


def evaluate_deterministic(rule, cases, pairs):
    cons = rule.get("constraints") or {}
    out = []
    for c in cases:
        res = {}
        for reading in ("strict", "lenient"):
            verdict, reasons = "pass", []
            for d, direction in pairs.items():
                smax, lmax, _ = thresholds(d, direction, cons)
                v, why = _verdict(c["example"], d, level(d, c["example"]), smax if reading == "strict" else lmax, cons)
                if v == "fail":
                    verdict = "fail"
                    reasons.append(why)
            res[reading] = (verdict, " ".join(reasons) or "Meets this reading of the rule.")
        out.append(_finish(c, res["strict"], res["lenient"], ["x"]))  # one deterministic pass
    return out


def _finish(c, strict, lenient, votes):
    sv, lv = strict[0], lenient[0]
    if sv == lv == "pass":
        assessment = "Likely compliant"
    elif sv == lv == "fail":
        assessment = "Potential violation"
    elif "unclear" in (sv, lv):
        assessment = "Uncertain"
    else:
        assessment = "Needs human review"
    agree = votes.count(votes[0]) / len(votes)
    confidence = "low" if agree < 0.67 else ("medium" if sv != lv or agree < 1 else "high")
    return {**c, "strict_verdict": sv, "strict_reason": strict[1], "lenient_verdict": lv, "lenient_reason": lenient[1],
            "assessment": assessment, "confidence": confidence, "self_consistent": agree == 1}


def suggest_clarification(text, dims, directions=None):
    directions = directions or {}
    snippets = [clarify_snippet(d, directions.get(d)) for d in dims]
    if not snippets:
        return ""
    return f"{text.rstrip('.')}. Specifically: " + "; ".join(snippets) + "."


AI_PREFIX = "ai:"


def dim_label(d):
    """Human label for a tested characteristic, including ones Gemini generated cases for."""
    if d in DIMS:
        return DIMS[d]["label"]
    if d.startswith(AI_PREFIX):
        return f"“{d[len(AI_PREFIX):]}” (Gemini-generated)"
    return d.capitalize()


def clarify_snippet(d, direction=None):
    if d in DIMS:
        return DIMS[d].get("clarify_toward", DIMS[d]["clarify"]) if direction == "toward" else DIMS[d]["clarify"]
    return f"what “{d[len(AI_PREFIX):]}” means in observable terms (for example, words to use or avoid)"
