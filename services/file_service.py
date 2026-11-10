"""Upload validation: extension, size, magic bytes, hashing and prompt-injection screening."""
import hashlib
import re
from pathlib import Path

import config


class FileRejected(ValueError):
    """Raised when an upload fails validation; message is safe to show to users."""


MAGIC = {".pdf": b"%PDF", ".docx": b"PK\x03\x04"}
INJECTION = re.compile(r"(ignore (all |any )?(previous|prior|above) instructions|disregard (the )?(system|previous)|"
                       r"you are now|act as (an?|the) |system prompt|reveal your|jailbreak)", re.I)


def validate_upload(name: str, data: bytes, allowed=None) -> str:
    allowed = allowed or config.ALLOWED_EXTENSIONS
    ext = Path(name).suffix.lower()
    if ext not in allowed:
        raise FileRejected(f"{name}: unsupported file type {ext or '(none)'}. Allowed: {', '.join(sorted(allowed))}.")
    if not data:
        raise FileRejected(f"{name}: the file is empty.")
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise FileRejected(f"{name}: file is larger than {config.MAX_UPLOAD_MB:g} MB.")
    magic = MAGIC.get(ext)
    if magic and not data.startswith(magic):
        raise FileRejected(f"{name}: the file content does not look like a real {ext} file.")
    return ext


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def injection_hits(text: str):
    """Phrases that look like instructions aimed at an AI. They are kept as data but flagged for the user."""
    return [m.group(0) for m in INJECTION.finditer(text or "")]
