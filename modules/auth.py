"""Sign-in for the BrandCanon MVP.

* Passwords are stored only as salted PBKDF2-SHA256 hashes (200,000 iterations) and compared in constant time.
* Error messages do not reveal whether the person or the password was wrong.
* Roles are still enforced in modules/access.py; signing in only establishes who is acting.

This is application-level sign-in for a prototype. It has no single sign-on, multi-factor authentication, password
recovery e-mails or server-side session store, and it is not presented as enterprise authentication.
"""
import hashlib
import hmac
import os

from database import db, repositories as repo
from modules.access import require

ITERATIONS = 200_000
MIN_LENGTH = 8
DEMO_PASSWORD = "novatech-demo"   # fictional demo accounts only; shown on the sign-in page
GENERIC_FAIL = "That password is not correct for this person."


class AuthError(ValueError):
    pass


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, digest = (stored or "").split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac("sha256", (password or "").encode(), bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(calc.hex(), digest)
    except (ValueError, TypeError):
        return False


def check_strength(password: str):
    if len(password or "") < MIN_LENGTH:
        raise AuthError(f"Use at least {MIN_LENGTH} characters for the password.")
    if (password or "").strip() != password:
        raise AuthError("The password cannot start or end with a space.")


def _set(user_id, password):
    check_strength(password)
    db.update("users", user_id, password_hash=hash_password(password))


def has_password(user_id) -> bool:
    u = repo.user(user_id)
    return bool(u and u.get("password_hash"))


def sign_in(user_id, password):
    """Return the user (without the hash) if the password is right; raise AuthError otherwise."""
    u = repo.user(user_id)
    if not u:
        raise AuthError("This person no longer exists. Choose someone else.")
    if not u.get("password_hash"):
        raise AuthError("This account has no password yet. Choose “Set a password” to activate it.")
    if not verify_password(password, u["password_hash"]):
        repo.log(u["workspace_id"], u["id"], "Failed sign-in")
        raise AuthError(GENERIC_FAIL)
    repo.log(u["workspace_id"], u["id"], "Signed in")
    return public(u)


def activate(user_id, password, confirm):
    """First-time password for an account created before sign-in existed (it has no password)."""
    if has_password(user_id):
        raise AuthError("This account already has a password. Sign in instead.")
    if password != confirm:
        raise AuthError("The two passwords do not match.")
    _set(user_id, password)
    u = repo.user(user_id)
    repo.log(u["workspace_id"], user_id, "Activated account")
    return public(u)


def workspace_name_taken(brand) -> bool:
    """True when a workspace with this exact name exists (used for the inline check on the sign-up page)."""
    brand = (brand or "").strip()
    return bool(brand and db.fetch_one("SELECT id FROM workspaces WHERE name = ?", (brand,)))


def create_workspace(brand, owner_name, password, confirm):
    """New workspace with its first Brand Manager. Returns the signed-in user."""
    brand, owner_name = (brand or "").strip(), (owner_name or "").strip()
    if not brand or not owner_name:
        raise AuthError("Enter the brand name and your name.")
    if db.fetch_one("SELECT id FROM workspaces WHERE name = ?", (brand,)):
        raise AuthError("A workspace with this name already exists. Ask its Brand Manager to add you.")
    if password != confirm:
        raise AuthError("The two passwords do not match.")
    check_strength(password)
    ws = repo.get_or_create_workspace(brand)
    uid = repo.get_or_create_user(ws, owner_name, "Brand Manager")
    db.update("users", uid, password_hash=hash_password(password))
    repo.log(ws, uid, "Created workspace", "workspace", ws, brand)
    return public(repo.user(uid))


def _clean_email(email):
    email = (email or "").strip().lower()
    if not email:
        return None
    if "@" not in email or email.startswith("@") or email.endswith("@") or " " in email:
        raise AuthError("Enter a valid e-mail address.")
    return email


def find_by_email(email):
    """The person whose Google account uses this e-mail, or None (matched case-insensitively)."""
    email = _clean_email(email)
    return repo.user_by_email(email) if email else None


def sign_in_google(email):
    """Sign in a person whose Google account was already verified by Google. Only people a Brand Manager added (or who
    created a workspace with Google) can sign in; an unknown e-mail never creates an account here."""
    u = find_by_email(email)
    if not u:
        raise AuthError("No BrandCanon account uses this Google e-mail yet.")
    repo.log(u["workspace_id"], u["id"], "Signed in with Google")
    return public(u)


def create_workspace_google(brand, owner_name, email):
    """New workspace whose first Brand Manager signs in with Google (no password is stored for this account)."""
    brand, owner_name, email = (brand or "").strip(), (owner_name or "").strip(), _clean_email(email)
    if not brand or not owner_name or not email:
        raise AuthError("Enter the brand name; your name and e-mail come from Google.")
    if find_by_email(email):
        raise AuthError("An account already uses this Google e-mail. Sign in instead.")
    if db.fetch_one("SELECT id FROM workspaces WHERE name = ?", (brand,)):
        raise AuthError("A workspace with this name already exists. Ask its Brand Manager to add you.")
    ws = repo.get_or_create_workspace(brand)
    uid = repo.get_or_create_user(ws, owner_name, "Brand Manager")
    db.update("users", uid, email=email)
    repo.log(ws, uid, "Created workspace (Google)", "workspace", ws, brand)
    return public(repo.user(uid))


def add_person(ws, actor_id, name, role, password, email=None):
    """Add a person. They sign in with a password, with Google (give their Google e-mail), or both."""
    require(actor_id, "Brand Manager")
    name = (name or "").strip()
    if not name:
        raise AuthError("Enter a name.")
    if role not in ("Creator", "Reviewer", "Brand Manager"):
        raise AuthError("Choose a role.")
    if db.fetch_one("SELECT id FROM users WHERE workspace_id = ? AND name = ? AND role = ?", (ws, name, role)):
        raise AuthError(f"{name} already has the {role} role here.")
    email = _clean_email(email)
    if email and find_by_email(email):
        raise AuthError("Another account already uses this e-mail.")
    if password or not email:   # a password is optional only when the person will use Google
        check_strength(password)
    uid = repo.get_or_create_user(ws, name, role)
    fields = {"email": email} if email else {}
    if password:
        fields["password_hash"] = hash_password(password)
    db.update("users", uid, **fields)
    repo.log(ws, actor_id, "Added person", "user", uid, f"{name} ({role})")
    return uid


def reset_password(ws, actor_id, target_id, password):
    require(actor_id, "Brand Manager")
    t = repo.user(target_id)
    if not t or t["workspace_id"] != ws:
        raise AuthError("That person is not in this workspace.")
    _set(target_id, password)
    repo.log(ws, actor_id, "Reset a password", "user", target_id, t["name"])


def change_password(user_id, current, new, confirm):
    u = repo.user(user_id)
    if not verify_password(current, u.get("password_hash")):
        raise AuthError("Your current password is not correct.")
    if new != confirm:
        raise AuthError("The two new passwords do not match.")
    _set(user_id, new)
    repo.log(u["workspace_id"], user_id, "Changed password")


def set_demo_passwords(ws):
    """All fictional demo accounts share DEMO_PASSWORD (hashed once, stored per user)."""
    h = hash_password(DEMO_PASSWORD)
    db.execute("UPDATE users SET password_hash = ? WHERE workspace_id = ?", (h, ws))


def public(u):
    return {k: v for k, v in dict(u).items() if k != "password_hash"}
