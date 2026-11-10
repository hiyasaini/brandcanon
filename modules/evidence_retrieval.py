"""Evidence retrieval over stored passages. Every hit carries its document, version, location and passage id.

BM25 keyword ranking boosted by document authority; if Gemini embeddings are available the top hits are
re-ranked semantically. Only current versions of active documents are searched unless asked otherwise.
"""
import math
import re
from collections import Counter

from database import repositories as repo
from services import embedding_service

STOP = set("a an the and or of to in on for with is are be was were it this that as at by from your our we you its "
           "into up than then so not no do does any all can will just".split())


def tokens(text):
    return [w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in STOP]


def _bm25(query, docs, k1=1.4, b=0.75):
    toks = [tokens(d) for d in docs]
    n = len(toks) or 1
    avg = (sum(map(len, toks)) / n) or 1
    df = Counter(w for t in toks for w in set(t))
    idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
    q = tokens(query)
    scores = []
    for t in toks:
        tf = Counter(t)
        scores.append(sum(idf.get(w, 0) * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(t) / avg)) for w in q) if t else 0)
    return scores


def search(ws, query, k=3, min_rank=0, current_only=True):
    ps = [p for p in repo.passages(ws, current_only) if (p["authority_rank"] or 0) >= min_rank]
    if not ps:
        return []
    scores = _bm25(query, [p["text"] for p in ps])
    ranked = sorted(((s * (1 + 0.08 * (p["authority_rank"] or 0)), p) for s, p in zip(scores, ps) if s > 0),
                    key=lambda x: -x[0])[: max(k * 3, k)]
    vecs = embedding_service.embed([query] + [p["text"] for _, p in ranked]) if ranked else None
    if vecs:
        qv = vecs[0]
        ranked = sorted(((0.5 * s / (ranked[0][0] or 1) + embedding_service.cosine(qv, v), p)
                         for (s, p), v in zip(ranked, vecs[1:])), key=lambda x: -x[0])
    return [dict(p, score=round(s, 3)) for s, p in ranked[:k]]


def search_rules(ws, query, k=5):
    rules = repo.list_rules(ws, ("Approved", "Pending Validation", "Needs Clarification"))
    if not rules:
        return []
    scores = _bm25(query, [r["text"] for r in rules])
    ranked = sorted(((s, r) for s, r in zip(scores, rules) if s > 0), key=lambda x: -x[0])
    return [dict(r, score=round(s, 3)) for s, r in ranked[:k]]


def cite(p):
    """Human-readable citation for a passage or rule/fact row joined with its source."""
    if not p:
        return "No stored source"
    title = p.get("doc_title") or "Unknown document"
    ver = p.get("version_label") or p.get("doc_version")
    loc = p.get("location") or ""
    return " · ".join(x for x in [title, f"v{ver}" if ver else "", loc] if x)
