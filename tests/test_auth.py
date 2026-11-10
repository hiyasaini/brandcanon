"""Sign-in: hashing, verification, roles, migration from schema v1."""
import sqlite3

import pytest

from database import db, repositories as repo
from modules import auth, demo
from modules.access import NotAuthorised


def test_hash_is_salted_and_verifies():
    a, b = auth.hash_password("correct horse"), auth.hash_password("correct horse")
    assert a != b and "correct horse" not in a
    assert auth.verify_password("correct horse", a) and not auth.verify_password("wrong", a)
    assert not auth.verify_password("x", None) and not auth.verify_password("x", "garbage")


def test_workspace_creation_and_sign_in(env):
    with pytest.raises(auth.AuthError):
        auth.create_workspace("Acme", "Asha", "short", "short")
    with pytest.raises(auth.AuthError):
        auth.create_workspace("Acme", "Asha", "long enough 1", "different 1")
    u = auth.create_workspace("Acme", "Asha", "long enough 1", "long enough 1")
    assert u["role"] == "Brand Manager" and "password_hash" not in u
    with pytest.raises(auth.AuthError) as e:
        auth.sign_in(u["id"], "nope nope")
    assert e.value.args[0] == auth.GENERIC_FAIL
    assert auth.sign_in(u["id"], "long enough 1")["name"] == "Asha"
    with pytest.raises(auth.AuthError):
        auth.create_workspace("Acme", "Someone", "long enough 1", "long enough 1")


def test_only_brand_manager_adds_people(env):
    uid = auth.add_person(env["ws"], env["bm"], "Zoe", "Creator", "zoe-password")
    assert auth.sign_in(uid, "zoe-password")["role"] == "Creator"
    with pytest.raises(NotAuthorised):
        auth.add_person(env["ws"], env["cr"], "Eve", "Brand Manager", "eve-password")
    auth.reset_password(env["ws"], env["bm"], uid, "new-password-1")
    assert auth.sign_in(uid, "new-password-1")
    auth.change_password(uid, "new-password-1", "newer-password", "newer-password")
    assert auth.sign_in(uid, "newer-password")


def test_legacy_account_activation(env):
    with pytest.raises(auth.AuthError) as e:
        auth.sign_in(env["rv"], "anything")
    assert "no password yet" in str(e.value)
    auth.activate(env["rv"], "reviewer-pass", "reviewer-pass")
    with pytest.raises(auth.AuthError):
        auth.activate(env["rv"], "other-pass-1", "other-pass-1")   # cannot be re-claimed
    assert auth.sign_in(env["rv"], "reviewer-pass")


def test_demo_accounts_have_demo_password(env):
    ws = demo.reset(with_history=False)
    neha = next(u for u in repo.users(ws) if u["name"] == "Neha")
    assert auth.sign_in(neha["id"], auth.DEMO_PASSWORD)["role"] == "Brand Manager"


def test_migration_from_v1_adds_password_column(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    c = sqlite3.connect(path)
    c.executescript("""CREATE TABLE schema_version (version INTEGER NOT NULL, applied_at TEXT NOT NULL);
        INSERT INTO schema_version VALUES (1, '2026-01-01');
        CREATE TABLE workspaces (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, is_demo INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
        CREATE TABLE users (id INTEGER PRIMARY KEY, workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          name TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE (workspace_id, name, role));
        INSERT INTO workspaces VALUES (1, 'Old', 0, '2026-01-01');
        INSERT INTO users VALUES (1, 1, 'Ola', 'Brand Manager', '2026-01-01');""")
    c.commit()
    c.close()
    monkeypatch.setenv("BRANDCANON_DB", str(path))
    db.reset_connections()
    db.init()
    assert db.fetch_one("SELECT MAX(version) v FROM schema_version")["v"] == db.SCHEMA_VERSION
    assert repo.user(1)["password_hash"] is None and repo.user(1)["name"] == "Ola"
    db.reset_connections()
