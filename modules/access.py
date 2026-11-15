"""Role checks enforced in the business layer (not only hidden in the UI)."""
from database import repositories as repo


class NotAuthorised(PermissionError):
    pass


def require(user_id, *roles):
    u = repo.user(user_id)
    if not u or u["role"] not in roles:
        who = f"{u['name']} ({u['role']})" if u else "Unknown user"
        raise NotAuthorised(f"{who} is not allowed to do this. Required role: {' or '.join(roles)}.")
    return u
