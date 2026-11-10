"""Optional semantic embeddings (Gemini). Retrieval works without them using BM25 (see evidence_retrieval)."""
import math

import config
from services import gemini_service

_cache = {}


def available():
    """Embeddings are opt-in (BRANDCANON_EMBEDDINGS=1) so retrieval does not spend Gemini quota by default."""
    return config.embeddings_enabled() and gemini_service.enabled()


def embed(texts):
    """Return a list of vectors, or None if embeddings are unavailable."""
    if not available():
        return None
    missing = [t for t in texts if t not in _cache]
    if missing:
        try:
            client = gemini_service._client_obj()
            resp = client.models.embed_content(model=config.embed_model(),
                                               contents=[gemini_service.redact(t) for t in missing])
            for t, e in zip(missing, resp.embeddings):
                _cache[t] = e.values
        except Exception as e:  # noqa: BLE001 — reported, then lexical (BM25) ranking is used
            gemini_service._record_failure(gemini_service.classify(e))
            return None
    return [_cache[t] for t in texts]


def cosine(a, b):
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0

