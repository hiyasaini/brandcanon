"""Pre-build the demonstration workspace so the first visitor does not wait for it.

Run after changing the demo data, the schema or the app version:  python scripts/build_demo_template.py
The app uses the file only when its stamp matches the running version and schema and it is under 7 days old (the demo's history is dated
relative to the build day); otherwise it builds the demo itself.
"""
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    tmp = Path(tempfile.mkdtemp()) / "t.db"
    os.environ.update(BRANDCANON_DB=str(tmp), AI_PROVIDER="deterministic", BRANDCANON_OFFLINE="1")
    import config
    from database import db
    from modules import demo
    db.reset_connections()
    db.init()
    demo.reset(with_history=True)
    db.conn().execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.reset_connections()
    out = ROOT / "assets" / "demo" / "demo_template.sqlite"
    out.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(tmp)
    c.execute("VACUUM")
    c.close()
    shutil.copy(tmp, out)
    out.with_suffix(".stamp").write_text(stamp(config, db))
    print("wrote", out, out.stat().st_size // 1024, "KB")


def stamp(config, db):
    import datetime
    return f"{config.APP_VERSION}/{db.SCHEMA_VERSION}/{datetime.date.today().isoformat()}"


if __name__ == "__main__":
    main()
