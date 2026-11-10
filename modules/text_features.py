"""Shared lexicons and deterministic text features. No AI is involved, so results are exact and reproducible."""
import re

EMOJI = re.compile("[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F☀-➿⭐⬆↔-↪]")
SLANG = {"lit", "fam", "besties", "bestie", "insane", "sooo", "soooo", "omg", "lol", "vibes", "slay", "bro", "dope",
         "goat", "epic", "literally", "yasss", "gonna", "wanna", "af", "lowkey", "highkey", "legit", "ngl", "tbh",
         "bruh", "hyped", "obsessed", "crazy", "ur", "u", "pls", "thx"}
INFORMAL = {"hey", "heyy", "heyyy", "hi", "yo", "awesome", "cool", "super", "guys", "folks", "gotta", "stoked", "wow",
            "yay", "ready"}
PRESSURE = ["buy now", "act now", "hurry", "don't miss", "dont miss", "last chance", "limited time", "regret",
            "before it's gone", "only today", "ends tonight", "order now", "grab it now", "now or never",
            "what are you waiting for", "shop now before"]
SUPERLATIVE = ["most powerful", "fastest", "best-in-class", "best in class", "the best", "#1", "number one", "no. 1",
               "ever made", "world's", "unbeatable", "ultimate", "revolutionary", "most advanced", "unmatched",
               "game-changing", "game changing", "perfect", "best"]
PROMISE = ["completely transform", "transform your", "change your life", "revolutionise", "revolutionize", "never again",
           "instantly", "effortlessly", "100% satisfaction", "will completely", "totally transform", "forever"]
ABSOLUTE = ["guaranteed", "guarantee", "guarantees", "100%", "never fails", "forever", "every situation", "risk-free",
            "lifetime", "unlimited", "zero risk", "always"]
FORMAL = ["cordially", "hereby", "commence", "utilise", "utilize", "utilisation", "pursuant", "henceforth", "esteemed",
          "endeavour", "aforementioned", "facilitate", "herein", "we invite you", "please be advised", "kindly note",
          "pleased to inform", "we wish to"]
AUDIENCES = {"gamers": "gamers", "gaming": "gamers", "gamer": "gamers", "kids": "children", "children": "children",
             "enterprise": "enterprises", "enterprises": "enterprises", "students": "students", "student": "students",
             "professionals": "professionals", "professional users": "professionals", "families": "families",
             "family": "families", "creators": "creators", "developers": "developers", "seniors": "seniors",
             "teens": "teenagers", "teenagers": "teenagers", "parents": "families", "businesses": "enterprises"}
CHANNEL_WORDS = {
    "instagram": "Instagram", "social media": "Social media", "social": "Social media", "twitter": "X / Twitter",
    "linkedin": "LinkedIn", "email": "Email marketing", "emails": "Email marketing", "newsletter": "Email marketing",
    "website": "Website", "web page": "Website", "product description": "Product descriptions", "print": "Print",
    "campaign": "Campaigns", "press release": "Press releases", "influencer": "Influencer partnerships",
    "advert": "Advertisements", "ads": "Advertisements", "advertisement": "Advertisements",
}
SOCIAL = {"Instagram", "X / Twitter", "LinkedIn", "Social media"}

UNIT_MAP = {"hours": "hours", "hour": "hours", "hrs": "hours", "hr": "hours", "h": "hours", "days": "days", "day": "days",
            "gb": "GB", "tb": "TB", "kg": "kg", "g": "g", "inch": "inch", "inches": "inch", "in": "inch", '"': "inch",
            "mp": "MP", "ghz": "GHz", "w": "W", "minutes": "minutes", "mins": "minutes", "min": "minutes",
            "%": "%", "mah": "mAh", "nits": "nits", "years": "years", "year": "years", "months": "months"}
NUM_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(hours?|hrs?|h\b|days?|gb|tb|kg|g\b|inch(?:es)?|in\b|\"|mp|ghz|w\b|"
                      r"minutes|mins?|%|mah|nits|years?|months)", re.I)
QUALIFIERS = ["up to", "under specified", "testing conditions", "typical", "approximately", "about", "around",
              "at least", "limited", "tested", "conditions", "usage", "may vary", "varies"]


def words(text):
    return re.findall(r"[A-Za-z']+", text.lower())


def sentences(text):
    """Split text into (start, end, sentence) spans."""
    out = []
    for m in re.finditer(r"(?:[^.!?\n]|(?<=\d)\.(?=\d)|(?<=\be\.g)\.|(?<=\bi\.e)\.)+(?:[.!?]+|$)", text):
        s = m.group(0)
        if s.strip():
            lead = len(s) - len(s.lstrip())
            out.append((m.start() + lead, m.end(), s.strip()))
    return out


def find_phrases(text, phrases):
    low = text.lower()
    hits = []
    for p in sorted(phrases, key=len, reverse=True):
        for m in re.finditer(r"(?<![\w])" + re.escape(p.lower()) + r"(?![\w])", low):
            if not any(m.start() < e and m.end() > s for s, e, _ in hits):
                hits.append((m.start(), m.end(), text[m.start():m.end()]))
    return sorted(hits)


def features(text):
    w = words(text)
    sents = [s for _, _, s in sentences(text)] or [text]
    return {
        "words": len(w),
        "emoji": len(EMOJI.findall(text)),
        "exclaim": text.count("!"),
        "slang": [x for x in w if x in SLANG]
                 + [m.group(0) for m in re.finditer(r"\b\w*([a-z])\1\1\w*\b", text.lower())],  # heyyy, sooo
        "informal": [x for x in w if x in INFORMAL],
        "pressure": [h[2] for h in find_phrases(text, PRESSURE)],
        "superlative": [h[2] for h in find_phrases(text, SUPERLATIVE)],
        "absolute": [h[2] for h in find_phrases(text, ABSOLUTE)],
        "formal": [h[2] for h in find_phrases(text, FORMAL)],
        "max_sentence_words": max(len(words(s)) for s in sents),
        "caps": [x for x in re.findall(r"\b[A-Z]{4,}\b", text) if x not in {"NOVATECH"}],
    }


def norm_unit(u):
    return UNIT_MAP.get(u.lower().strip(), u.lower())


def num_units(text):
    return [(float(m.group(1)), norm_unit(m.group(2)), m.start(), m.end()) for m in NUM_UNIT.finditer(text)]


def channels_in(text):
    low = text.lower()
    found = []
    for k, v in CHANNEL_WORDS.items():
        if re.search(r"\b" + re.escape(k) + r"\b", low) and v not in found:
            found.append(v)
    return found
