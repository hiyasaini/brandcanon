"""Find a Gemini model that actually answers for YOUR key, and save it to .env.

Run:  python scripts/find_model.py

It lists the models your key can use, tries the fast ones first with one tiny request each, and writes the first one
that answers into .env as GEMINI_MODEL. The API key is read from .env and is never printed.
"""
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402  (loads .env)

SKIP = ("embedding", "image", "tts", "audio", "live", "vision", "aqa", "imagen", "veo", "learnlm", "gemma", "robotics",
        "computer-use", "native")


def rank(name):
    n = name.lower()
    if "flash-lite" in n:
        score = 0
    elif "flash" in n:
        score = 1
    elif "pro" in n:
        score = 3
    else:
        score = 2
    return (score, "preview" in n or "exp" in n, n)


def save(model):
    env = ROOT / ".env"
    lines = env.read_text().splitlines() if env.exists() else []
    lines = [ln for ln in lines if not ln.strip().startswith("GEMINI_MODEL=")] + [f"GEMINI_MODEL={model}"]
    env.write_text("\n".join(lines) + "\n")


def main():
    key = config.gemini_key()
    if not key:
        print("GEMINI_API_KEY is not set in .env. Add it, then run this again.")
        return 1
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=60_000))
    try:
        models = list(client.models.list())
    except Exception as e:  # noqa: BLE001
        print(f"Could not list models: {type(e).__name__}: {str(e).replace(key, '[key]')[:300]}")
        return 1
    names = []
    for m in models:
        name = (m.name or "").replace("models/", "")
        actions = getattr(m, "supported_actions", None) or []
        if actions and "generateContent" not in actions:
            continue
        if not name.startswith("gemini") or any(s in name.lower() for s in SKIP):
            continue
        names.append(name)
    names = sorted(set(names), key=rank)
    if not names:
        print("Your key lists no Gemini text models. Check the key's project in Google AI Studio.")
        return 1
    print(f"Your key can use {len(names)} Gemini text models. Trying the fastest first…\n")
    for name in names[:10]:
        t0 = time.time()
        try:
            r = client.models.generate_content(model=name, contents="Reply with the single word OK.")
            text = (r.text or "").strip()
            if text:
                save(name)
                print(f"  {name:40s} answered in {time.time() - t0:.1f}s: {text[:40]!r}")
                print(f"\nSaved GEMINI_MODEL={name} to .env. Now run:  python scripts/check_gemini.py")
                return 0
            print(f"  {name:40s} returned no text")
        except Exception as e:  # noqa: BLE001
            msg = str(e).replace(key, "[key]").split("\n")[0][:110]
            print(f"  {name:40s} failed: {type(e).__name__}: {msg}")
    print("\nNo model answered. Google's service may be busy for your key right now — wait 10–15 minutes and run this again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
