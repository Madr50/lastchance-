# README for migrations

This migrations folder contains SQL migrations and a small runner to apply them to the project's SQLite database (shop.db).

How to run
1. Create a python venv and install requirements if not already:
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

2. Make a local backup (the script also attempts to backup):
   cp shop.db shop.db.localbackup

3. Apply migrations:
   python migrations/run_migrations.py shop.db

Notes
- The runner is intentionally simple. For production systems, consider migrating to a proper migration tool (alembic or similar) and migrating to PostgreSQL.
- The script will create tables using IF NOT EXISTS to preserve existing data.
