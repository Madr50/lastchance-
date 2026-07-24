#!/usr/bin/env python3
"""
run_migrations.py
Simple migration runner for the SQLite-based marketplace.
Usage: python migrations/run_migrations.py [path_to_db]
Defaults to shop.db in repository root.

This script will:
 - Backup the existing database to shop.db.backup (if present)
 - Apply SQL migrations in order (only the first migration exists for now)
"""
import sqlite3
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / 'shop.db'
MIGRATION_SQL = REPO_ROOT / 'migrations' / '0001_create_marketplace_schema.sql'

def backup_db(db_path: Path):
    if not db_path.exists():
        print(f"Database not found at {db_path}, skipping backup.")
        return
    backup_path = db_path.with_suffix(db_path.suffix + '.backup')
    if backup_path.exists():
        print(f"Backup already exists at {backup_path}.")
    else:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Created backup: {backup_path}")


def run_migration(db_path: Path):
    if not MIGRATION_SQL.exists():
        print(f"Migration file not found: {MIGRATION_SQL}")
        return

    sql = MIGRATION_SQL.read_text(encoding='utf-8')

    conn = sqlite3.connect(str(db_path))
    conn.execute('PRAGMA foreign_keys = ON;')
    cur = conn.cursor()
    try:
        cur.executescript(sql)
        conn.commit()
        print('Migrations applied successfully.')
    except Exception as e:
        conn.rollback()
        print('Migration failed:', e)
    finally:
        conn.close()


if __name__ == '__main__':
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    print(f"Using database: {db}")
    backup_db(db)
    run_migration(db)
