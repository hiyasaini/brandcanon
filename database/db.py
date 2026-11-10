"""SQLite connection, transactions, initialisation and migrations.

All SQL elsewhere uses parameter binding; table/column names passed to the generic helpers come from code,
never from user input (they are checked against the live schema before use).
"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

import config

SCHEMA_VERSION = 3
_lock = threading.RLock()
_local = threading.local()
_columns = {}


class DatabaseError(RuntimeError):
    """Raised for database failures with a user-presentable message."""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    path = config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # isolation_level=None -> we control transactions explicitly with BEGIN/COMMIT in transaction()
    conn = sqlite3.connect(path, check_same_thread=False, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def conn() -> sqlite3.Connection:
    key = str(config.db_path())
    c = getattr(_local, "conns", {}).get(key)
    if c is None:
        _local.conns = getattr(_local, "conns", {})
        c = _local.conns[key] = _connect()
    return c


def reset_connections():
    """Close cached connections (used by tests and when the DB file is replaced)."""
    for c in getattr(_local, "conns", {}).values():
        c.close()
    _local.conns = {}
    _columns.clear()


@contextmanager
def transaction():
    """Atomic unit of work: commits on success, rolls back on any error."""
    c = conn()
    with _lock:
        try:
            c.execute("BEGIN")
            yield c
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise


def init():
    """Create tables and apply migrations. Safe to call on every start."""
    try:
        c = conn()
        with _lock:
            c.executescript(config.SCHEMA_FILE.read_text())
            cur = c.execute("SELECT MAX(version) v FROM schema_version").fetchone()["v"]
            if cur is None:
                c.execute("INSERT INTO schema_version(version, applied_at) VALUES (?, ?)", (SCHEMA_VERSION, now()))
            elif cur < SCHEMA_VERSION:
                _migrate(c, cur)
            c.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Could not initialise the database: {e}") from e


def _migrate(c, from_version):
    """Apply each step after `from_version`, in order, inside init()'s transaction."""
    if from_version < 2:  # v2: sign-in passwords (salted PBKDF2 hashes)
        cols = {r["name"] for r in c.execute("PRAGMA table_info(users)").fetchall()}
        if "password_hash" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if from_version < 3:  # v3: document review status; RuleProbe investigation workflow
        def add(table, col, ddl):
            if col not in {r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        add("documents", "review_status", "review_status TEXT NOT NULL DEFAULT 'Pending review' "
            "CHECK (review_status IN ('Pending review', 'Approved', 'Rejected', 'Archived'))")
        add("documents", "review_note", "review_note TEXT")
        add("rule_tests", "investigation_state", "investigation_state TEXT NOT NULL DEFAULT 'draft' "
            "CHECK (investigation_state IN ('draft', 'saved', 'in_review', 'approved', 'rule_updated'))")
        add("rule_tests", "notes", "notes TEXT")
        c.execute("UPDATE documents SET review_status = 'Archived' WHERE status = 'archived'")
        c.execute("UPDATE rule_tests SET investigation_state = CASE resolution WHEN 'keep' THEN 'approved' "
                  "WHEN 'clarify' THEN 'rule_updated' ELSE investigation_state END WHERE status = 'resolved'")
    c.execute("INSERT INTO schema_version(version, applied_at) VALUES (?, ?)", (SCHEMA_VERSION, now()))
    _columns.clear()


def _cols(table):
    if table not in _columns:
        rows = conn().execute(f"PRAGMA table_info({table})").fetchall()  # table names are code constants
        if not rows:
            raise DatabaseError(f"Unknown table {table}")
        _columns[table] = {r["name"] for r in rows}
    return _columns[table]


def _check(table, keys):
    bad = set(keys) - _cols(table)
    if bad:
        raise DatabaseError(f"Unknown column(s) {bad} for {table}")


def insert(table, c=None, **data):
    _check(table, data)
    sql = f"INSERT INTO {table} ({', '.join(data)}) VALUES ({', '.join('?' * len(data))})"
    try:
        if c is not None:
            return c.execute(sql, list(data.values())).lastrowid
        with transaction() as t:
            return t.execute(sql, list(data.values())).lastrowid
    except sqlite3.IntegrityError as e:
        raise DatabaseError(f"Could not save to {table}: {e}") from e


def update(table, row_id, c=None, **data):
    _check(table, data)
    sql = f"UPDATE {table} SET {', '.join(f'{k} = ?' for k in data)} WHERE id = ?"
    try:
        if c is not None:
            c.execute(sql, [*data.values(), row_id])
            return
        with transaction() as t:
            t.execute(sql, [*data.values(), row_id])
    except sqlite3.IntegrityError as e:
        raise DatabaseError(f"Could not update {table}: {e}") from e


def execute(sql, params=(), c=None):
    if c is not None:
        return c.execute(sql, params)
    with transaction() as t:
        return t.execute(sql, params)


def fetch_all(sql, params=()):
    with _lock:
        return [dict(r) for r in conn().execute(sql, params).fetchall()]


def fetch_one(sql, params=()):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def get(table, row_id):
    _cols(table)
    return fetch_one(f"SELECT * FROM {table} WHERE id = ?", (row_id,))
