"""Check live Gemini connectivity from the command line:  python scripts/check_gemini.py

Reads GEMINI_API_KEY, GEMINI_MODEL and AI_PROVIDER from .env (python-dotenv). Sends ONE short request with the
official google-genai SDK and prints the reply. The key itself is never printed.
Exit code 0 = Gemini answered; 1 = not configured; 2 = the request failed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402  (loads .env)
from services import gemini_service as gs  # noqa: E402


def main():
    print(f"AI_PROVIDER    = {config.ai_provider()}")
    print(f"GEMINI_MODEL   = {gs.model()}")
    print(f"GEMINI_API_KEY = {'set (hidden)' if config.gemini_key() else 'NOT SET'}")
    st = gs.status()
    if st["mode"] != "gemini":
        print(f"\nNot checking: {st['problem'] or 'AI_PROVIDER is not gemini.'}")
        print("Add AI_PROVIDER=gemini and GEMINI_API_KEY=... to .env, then run this again.")
        return 1
    print("\nSending one short request to Gemini…")
    out = gs.check_connection()
    if out["ok"]:
        print(f"OK — {out['message']}\nReply: {out['reply']}")
        return 0
    print(f"FAILED ({out['kind']}): {out['message']}")
    if out.get("detail"):
        print(f"Detail (key removed): {out['detail']}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
