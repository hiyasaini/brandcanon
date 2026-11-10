"""Central configuration. Values come from environment variables (optionally a .env file)."""
import os
from pathlib import Path

try:  # optional: load .env for local development
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SAMPLE_DIR = ROOT / "assets" / "sample_brand"
SCHEMA_FILE = ROOT / "database" / "schema.sql"


def _session_db_path():
    """In public mode each browser session works on its own copy of the database (set by app.py)."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx(suppress_warning=True) is None:
            return None
        import streamlit as st
        p = st.session_state.get("_db_path")
        return Path(p) if p else None
    except Exception:  # not running under Streamlit
        return None


def db_path() -> Path:
    sp = _session_db_path()
    if sp is not None:
        return sp
    p = Path(os.environ.get("BRANDCANON_DB", DATA_DIR / "brandcanon.db"))
    return p if p.is_absolute() else ROOT / p


def _setting(name, default=None):
    """Environment variable first (.env is loaded above), then Streamlit secrets (for Streamlit Cloud)."""
    val = os.environ.get(name)
    if val is not None and val.strip() != "":
        return val.strip()
    try:
        import streamlit as st
        val = st.secrets.get(name)
        return str(val).strip() if val not in (None, "") else default
    except Exception:  # no secrets file, or not running under Streamlit
        return default


PLACEHOLDER_KEYS = {"", "your-key-here", "your_api_key", "changeme", "<your key>", "paste-your-key-here"}


def gemini_key():
    """The Gemini API key, or None. Never log or display this value."""
    key = _setting("GEMINI_API_KEY")
    return None if key is None or key.lower() in PLACEHOLDER_KEYS else key


def ai_provider() -> str:
    """'gemini' selects live Gemini; 'deterministic' uses application logic only. When AI_PROVIDER is not set at all,
    Gemini is switched on automatically if a key is present, so a deployment only needs GEMINI_API_KEY."""
    default = "gemini" if gemini_key() else "deterministic"
    return (_setting("AI_PROVIDER", default) or default).lower()


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def gemini_model() -> str:
    return _setting("GEMINI_MODEL", DEFAULT_GEMINI_MODEL) or DEFAULT_GEMINI_MODEL


def gemini_timeout_s() -> float:
    try:
        return float(_setting("GEMINI_TIMEOUT_SECONDS", 120))
    except ValueError:
        return 120.0


def embeddings_enabled() -> bool:
    return _setting("BRANDCANON_EMBEDDINGS", "0") == "1"


def embed_model() -> str:
    return _setting("GEMINI_EMBED_MODEL", "gemini-embedding-001")


MAX_UPLOAD_MB = float(os.environ.get("BRANDCANON_MAX_UPLOAD_MB", 15))
ALLOWED_EXTENSIONS = {".pdf", ".docx"}  # manual document uploads only
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def public_mode() -> bool:
    """BRANDCANON_PUBLIC=1 (for a shared link): every visitor gets a private copy of the demo database."""
    return _setting("BRANDCANON_PUBLIC", "0") == "1"


def offline_forced() -> bool:
    return os.environ.get("BRANDCANON_OFFLINE", "0") == "1"


# ---------------------------------------------------------------- domain vocabularies
ROLES = ("Creator", "Reviewer", "Brand Manager")

# label -> rank (higher = more authoritative)
AUTHORITY_LEVELS = {
    "Official Product Specification": 5,
    "Official Brand Guideline": 4,
    "Approved Policy": 4,
    "Approved Campaign Document": 3,
    "Official Web Page": 3,
    "Older Marketing Presentation": 1,
    "Informal Note": 0,
}

KNOWLEDGE_CATEGORIES = [
    "Brand tone", "Brand personality", "Terminology", "Messaging", "Product specifications", "Approved claims",
    "Prohibited claims", "Campaign instructions", "Visual identity", "Accessibility requirements", "Other policies",
]

# Stored category -> the name shown in the interface (the brief's knowledge categories)
DISPLAY_CATEGORY = {
    "Brand personality": "Brand voice", "Brand tone": "Tone and personality", "Terminology": "Terminology",
    "Messaging": "Messaging", "Product specifications": "Product facts", "Approved claims": "Approved claims",
    "Prohibited claims": "Restricted claims", "Visual identity": "Visual identity",
    "Accessibility requirements": "Accessibility", "Campaign instructions": "Campaign instructions",
    "Other policies": "Other policies",
}

RULE_STATUSES = ("Pending Validation", "Approved", "Rejected", "Needs Clarification", "Archived")

CHANNELS = ["All content", "Social media", "Instagram", "X / Twitter", "LinkedIn", "Email marketing", "Website",
            "Product descriptions", "Advertisements", "Campaigns", "Press releases", "Influencer partnerships", "Print"]
CONTENT_TYPES = ["Social media caption", "Marketing email", "Advertisement", "Product description", "Website copy",
                 "Campaign text"]

FINDING_CLASSES = ("Contradicted", "Unsupported", "Unverifiable", "Verified", "Violation", "Needs review")
ROOT_CAUSES = ("Creator error", "Guideline defect", "Source conflict", "Knowledge gap", "Unresolved / other")
PROBE_CLASSES = ("Ambiguous rule", "Contradictory rules", "Missing guidance", "Model uncertainty", "Clear rule")
