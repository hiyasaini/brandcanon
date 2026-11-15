"""Storage for the measured accuracy benchmark: imported labelled sets and one stored result per app version and engine."""
import json

import config
from database import db
from modules import evaluation
from modules.access import require

MAX_ITEMS = 500
MAX_TEXT = 600


class BenchmarkError(ValueError):
    pass


TEMPLATE = {
    "source": "Name of the guideline set these items come from, e.g. 'Acme public brand guidelines (acme.com/brand)'",
    "rules": [{"text": "Keep a friendly tone.", "label": "ambiguous"},
              {"text": "Use at most 20 words per sentence.", "label": "clear"}],
    "pairs": [{"a": "Always use formal language.", "b": "Use casual language on social media.", "label": "conflict"}],
    "claims": [{"text": "Our battery lasts 3 days.", "label": "flag", "product": "optional product name"}],
    "_labels": {"rules": "ambiguous | clear", "pairs": "conflict | none", "claims": "flag | ok"},
}


def template_json():
    return json.dumps(TEMPLATE, indent=2)


def parse(raw: bytes):
    """Validate an uploaded JSON file. Returns (source, {kind: [items]}). Anything not recognised is refused, never guessed."""
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as e:
        raise BenchmarkError("This is not a valid JSON file.") from e
    if not isinstance(data, dict):
        raise BenchmarkError("The file must be a JSON object (see the template).")
    source = str(data.get("source") or "").strip()
    if len(source) < 3 or source.startswith("Name of the guideline set"):
        raise BenchmarkError("Say where the items come from in \"source\" (for example the brand and the guideline's address).")
    out, total = {}, 0
    for kind, (pos, neg) in evaluation.LABELS.items():
        items = data.get(kind) or []
        if not isinstance(items, list):
            raise BenchmarkError(f"\"{kind}\" must be a list.")
        fields = ("a", "b") if kind == "pairs" else ("text",)
        clean = []
        for i, it in enumerate(items, 1):
            if not isinstance(it, dict) or it.get("label") not in (pos, neg):
                raise BenchmarkError(f"{kind} item {i}: label must be \"{pos}\" or \"{neg}\".")
            row = {"label": it["label"]}
            for f in fields:
                v = " ".join(str(it.get(f) or "").split())
                if not v or len(v) > MAX_TEXT:
                    raise BenchmarkError(f"{kind} item {i}: \"{f}\" must be 1–{MAX_TEXT} characters.")
                row[f] = v
            if kind == "claims" and it.get("product"):
                row["product"] = str(it["product"])[:80]
            clean.append(row)
        if clean:
            out[kind] = clean
        total += len(clean)
    if not total:
        raise BenchmarkError("The file has no labelled items.")
    if total > MAX_ITEMS:
        raise BenchmarkError(f"Import at most {MAX_ITEMS} items at a time.")
    return source[:120], out


def import_set(ws, user_id, raw: bytes, name=None):
    require(user_id, "Brand Manager")
    source, kinds = parse(raw)
    with db.transaction() as c:
        for kind, items in kinds.items():
            db.insert("eval_sets", c=c, workspace_id=ws, name=(name or source)[:80], source=source, kind=kind,
                      payload=json.dumps(items), item_count=len(items), created_by=user_id, created_at=db.now())
    return sum(len(v) for v in kinds.values())


def sets(ws):
    return db.fetch_all("SELECT * FROM eval_sets WHERE workspace_id = ? ORDER BY id", (ws,))


def delete_set(ws, user_id, source):
    require(user_id, "Brand Manager")
    db.execute("DELETE FROM eval_sets WHERE workspace_id = ? AND source = ?", (ws, source))


def store(ws, result, note=""):
    summary = {k: result[k]["metrics"] for k in ("rules", "pairs", "claims")}
    summary["gemini_failed"] = result.get("gemini_failed", 0)
    return db.insert("eval_runs", workspace_id=ws, app_version=config.APP_VERSION, engine=result["engine"],
                     item_counts=json.dumps(result["counts"]), metrics=json.dumps(summary), note=note, created_at=db.now())


def runs(ws=None):
    rows = db.fetch_all("SELECT * FROM eval_runs ORDER BY id")
    return [dict(r, metrics=json.loads(r["metrics"]), item_counts=json.loads(r["item_counts"])) for r in rows]


def ensure_current(demo_ws, ws):
    """Make sure the built-in engine has a stored result for this app version (so every release shows its score)."""
    if any(r["app_version"] == config.APP_VERSION and r["engine"] == "built-in" for r in runs()):
        return None
    res = evaluation.run_all(demo_ws, sets(ws), False)
    store(ws, res, "automatic first run for this version")
    return res
