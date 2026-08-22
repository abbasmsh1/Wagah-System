"""Periodic SQLite backup.

Snapshots the whole database with SQLite's online backup API (safe while the
app is running) into BACKUP_DIR, and optionally into BACKUP_EXTERNAL_DIR.
Restore = stop the app and copy the snapshot back over the database file.

Run alongside the app:  python backup.py
"""
import logging
import os
import sqlite3
import time

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wagah.db")
if not DATABASE_URL.startswith("sqlite"):
    raise SystemExit("backup.py only supports SQLite; use pg_dump or similar for other databases.")
DB_PATH = DATABASE_URL.split("///", 1)[1]

BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
EXTERNAL_DIR = os.getenv("BACKUP_EXTERNAL_DIR")  # optional second copy, e.g. a mounted drive
INTERVAL_SECONDS = int(os.getenv("BACKUP_INTERVAL_SECONDS", "3600"))

def backup_to(target_dir: str) -> None:
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, "wagah_backup.db")
    with sqlite3.connect(DB_PATH) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    logger.info("Backup written to %s", target)

def backup_database() -> None:
    backup_to(BACKUP_DIR)
    if EXTERNAL_DIR:
        try:
            backup_to(EXTERNAL_DIR)
        except OSError:
            logger.exception("External backup to %s failed", EXTERNAL_DIR)

if __name__ == "__main__":
    while True:
        try:
            backup_database()
        except Exception:
            logger.exception("Backup failed")
        time.sleep(INTERVAL_SECONDS)
