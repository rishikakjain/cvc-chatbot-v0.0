"""
Migrate course data from local SQLite (courses.db) to Aurora Serverless v2 PostgreSQL.

Prerequisites:
  - Aurora cluster is AVAILABLE (run scripts/setup_rds.py first)
  - SECRET_ARN env var is set (output of setup_rds.py)
  - DB_HOST env var is set (cluster endpoint, output of setup_rds.py)
  - Run from a machine with VPC access (or via a bastion / AWS Cloud9 in the VPC)

Usage:
    SECRET_ARN=arn:aws:... DB_HOST=<cluster-endpoint> python data/migrate_to_postgres.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

SQLITE_PATH = ROOT / "data" / "courses.db"
SCHEMA_PG   = ROOT / "data" / "schema_pg.sql"


def _get_sqlite_conn():
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _get_pg_conn():
    import boto3
    import psycopg2
    import psycopg2.extras

    secret_arn = os.environ["SECRET_ARN"]
    region     = os.environ.get("AWS_REGION", "us-west-2")
    sm         = boto3.client("secretsmanager", region_name=region)
    creds      = json.loads(sm.get_secret_value(SecretId=secret_arn)["SecretString"])

    return psycopg2.connect(
        host=creds["host"],
        port=int(creds.get("port", 5432)),
        dbname=creds.get("dbname", os.environ.get("DB_NAME", "cvcdb")),
        user=creds["username"],
        password=creds["password"],
        connect_timeout=10,
        sslmode="require",
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def migrate():
    print("Connecting to SQLite …")
    sqlite_conn = _get_sqlite_conn()

    print("Connecting to PostgreSQL (fetching credentials from Secrets Manager) …")
    pg_conn = _get_pg_conn()
    pg_cur  = pg_conn.cursor()

    print("Creating schema …")
    pg_cur.execute(SCHEMA_PG.read_text())
    pg_conn.commit()

    # ── Colleges ──────────────────────────────────────────────────────────────
    colleges = sqlite_conn.execute("SELECT * FROM colleges").fetchall()
    print(f"Migrating {len(colleges)} colleges …")
    for row in colleges:
        pg_cur.execute(
            """
            INSERT INTO colleges (name, name_lower, lat, lng, region)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            (row["name"], row["name_lower"], row["lat"], row["lng"], row["region"]),
        )
    pg_conn.commit()
    print(f"  ✓ {len(colleges)} colleges inserted")

    # ── Courses ───────────────────────────────────────────────────────────────
    courses = sqlite_conn.execute("SELECT * FROM courses").fetchall()
    print(f"Migrating {len(courses)} courses …")

    _JSON_COLS = ("badges", "csu_breadth", "igetc", "cal_getc")

    for row in courses:
        def col(name):
            v = row[name]
            if name in _JSON_COLS:
                # SQLite stores as JSON text; Postgres needs a Python list
                if isinstance(v, str):
                    try:
                        return json.loads(v)
                    except Exception:
                        return []
                return v or []
            return v

        pg_cur.execute(
            """
            INSERT INTO courses (
                course_code, course_name, cid, section, crn,
                start_date, end_date, term, teaching_college, delivery_method,
                badges, csu_breadth, igetc, cal_getc,
                professors, units, visible, filter_applied, course_notes,
                seat_count, seats_available, seat_count_updated_at, source_file
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (crn) DO NOTHING
            """,
            (
                col("course_code"), col("course_name"), col("cid"), col("section"), col("crn"),
                col("start_date"), col("end_date"), col("term"), col("teaching_college"), col("delivery_method"),
                json.dumps(col("badges")), json.dumps(col("csu_breadth")),
                json.dumps(col("igetc")), json.dumps(col("cal_getc")),
                col("professors"), col("units"), bool(col("visible")), bool(col("filter_applied")),
                col("course_notes"), col("seat_count"), col("seats_available"),
                col("seat_count_updated_at"), col("source_file"),
            ),
        )

    pg_conn.commit()
    print(f"  ✓ {len(courses)} courses inserted")

    pg_cur.close()
    pg_conn.close()
    sqlite_conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    if "SECRET_ARN" not in os.environ:
        print("ERROR: SECRET_ARN env var required. Run scripts/setup_rds.py first.")
        sys.exit(1)
    migrate()
