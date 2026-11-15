"""Stay signed in after a browser refresh: a signed, expiring token kept in a cookie.

The token holds only the person's id, an expiry and a short fingerprint of their password hash (so changing the password
ends old sessions). It is signed with a random key generated on this server; it is not a password and cannot be forged
without that key. Signing out clears it. A server restart that loses the key simply signs people out.
"""
import base64
import hashlib
import hmac
import secrets
import tempfile
import time
from pathlib import Path

import config

COOKIE = "bc_session"
LIFETIME = 8 * 3600


def _key() -> bytes:
    for d in (config.DATA_DIR, Path(tempfile.gettempdir())):
        p = d / ".session_key"
        try:
            if p.exists():
                return bytes.fromhex(p.read_text().strip())
            d.mkdir(parents=True, exist_ok=True)
            k = secrets.token_hex(32)
            p.write_text(k)
            p.chmod(0o600)
            return bytes.fromhex(k)
        except (OSError, ValueError):
            continue
    return b"brandcanon-ephemeral-" + str(id(_key)).encode()   # last resort: valid for this process only


def _fp(user) -> str:
    return hashlib.sha256((user.get("password_hash") or "x").encode()).hexdigest()[:10]


def issue(user, now=None) -> str:
    body = f"{user['id']}.{int((now or time.time()) + LIFETIME)}.{_fp(user)}"
    sig = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(f"{body}.{sig}".encode()).decode()


def verify(token, load_user, now=None):
    """Return the user row for a valid token, else None. `load_user(id)` fetches a user by id."""
    try:
        body, sig = base64.urlsafe_b64decode(token.encode()).decode().rsplit(".", 1)
        uid, exp, fp = body.split(".")
        good = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, good) or int(exp) < (now or time.time()):
            return None
        user = load_user(int(uid))
    except (ValueError, TypeError, UnicodeError, AttributeError):
        return None
    return user if user and _fp(user) == fp else None
