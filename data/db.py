"""
Database connection helpers for the CVC course database.

Local dev: uses SQLite (courses.db, no env vars needed).
Lambda/prod: reads SECRET_ARN env var → fetches credentials from AWS Secrets Manager
             → connects to Aurora Serverless v2 via psycopg2.

The public surface is the same in both modes:
    conn = get_connection()
    rows = execute(conn, "SELECT * FROM courses WHERE visible = TRUE")
    dicts = [row_to_dict(r) for r in rows]
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).parent / "courses.db"
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

_COL_MAP = {
    "course_code":           "courseCode",
    "course_name":           "courseName",
    "cid":                   "cid",
    "section":               "section",
    "crn":                   "crn",
    "start_date":            "startDate",
    "end_date":              "endDate",
    "term":                  "term",
    "teaching_college":      "teachingCollege",
    "delivery_method":       "deliveryMethod",
    "badges":                "badges",
    "csu_breadth":           "csuBreadth",
    "igetc":                 "igetc",
    "cal_getc":              "calGetc",
    "professors":            "professors",
    "units":                 "units",
    "visible":               "visible",
    "filter_applied":        "filterApplied",
    "course_notes":          "courseNotes",
    "seat_count":            "seatCount",
    "seats_available":       "seatsAvailable",
    "seat_count_updated_at": "seatCountUpdatedAt",
}

# Columns that are stored as JSON text in SQLite (but JSONB in Postgres)
_JSON_COLS = {"badges", "csu_breadth", "igetc", "cal_getc"}

_region_cache: dict[str, str] | None = None
_pg_credentials: dict | None = None


# ── Credential helpers ────────────────────────────────────────────────────────

def _fetch_pg_credentials() -> dict:
    """Fetch DB credentials from Secrets Manager (cached per Lambda container)."""
    global _pg_credentials
    if _pg_credentials is not None:
        return _pg_credentials
    import boto3
    secret_arn = os.environ["SECRET_ARN"]
    region = os.environ.get("AWS_REGION", "us-west-2")
    client = boto3.client("secretsmanager", region_name=region)
    secret = client.get_secret_value(SecretId=secret_arn)
    _pg_credentials = json.loads(secret["SecretString"])
    return _pg_credentials


def _is_postgres() -> bool:
    return "SECRET_ARN" in os.environ


# ── Connection factory ────────────────────────────────────────────────────────

def get_connection(db_path: str | Path | None = None):
    """Return a live database connection (SQLite or psycopg2)."""
    if _is_postgres():
        return _get_pg_connection()
    return get_db(db_path)


def _get_pg_connection():
    """Open a psycopg2 connection to Aurora using Secrets Manager credentials."""
    import psycopg2
    import psycopg2.extras
    creds = _fetch_pg_credentials()
    conn = psycopg2.connect(
        host=creds["host"],
        port=int(creds.get("port", 5432)),
        dbname=creds.get("dbname", os.environ.get("DB_NAME", "cvcdb")),
        user=creds["username"],
        password=creds["password"],
        connect_timeout=10,
        sslmode="require",
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    return conn


# ── SQLite helpers (kept for local dev and tests) ────────────────────────────

def get_db(path: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path or _DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_PATH.read_text())
    conn.commit()


# ── Row → camelCase dict ─────────────────────────────────────────────────────

def row_to_dict(row: Any) -> dict:
    """
    Convert a DB row to the camelCase dict shape the rest of the app expects.

    Works for both sqlite3.Row (key-indexed) and psycopg2 RealDictRow.
    In Postgres, array columns are already Python lists (JSONB); in SQLite
    they are JSON text that we decode here.
    """
    # psycopg2 RealDictCursor rows are already dicts
    if isinstance(row, dict):
        raw = row
    else:
        # sqlite3.Row — convert to plain dict
        raw = {col: row[col] for col in row.keys()}

    result: dict = {}
    for col, camel in _COL_MAP.items():
        val = raw.get(col)
        if col in _JSON_COLS:
            # SQLite stores as JSON text; Postgres returns a Python list already
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    val = []
            elif val is None:
                val = []
        elif col in ("visible", "filter_applied"):
            val = bool(val)
        result[camel] = val
    return result


# ── Generic query helper ─────────────────────────────────────────────────────

def execute(conn, query: str, params: tuple = ()) -> list[dict]:
    """Run a SELECT and return rows as camelCase dicts. Works for both backends."""
    if _is_postgres():
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [row_to_dict(dict(r)) for r in rows]
    else:
        rows = conn.execute(query, params).fetchall()
        return [row_to_dict(r) for r in rows]


# ── College region lookup ────────────────────────────────────────────────────

def get_college_region_from_db(college_name_lower: str, db_path: str | Path | None = None) -> str:
    global _region_cache
    if _region_cache is None:
        try:
            conn = get_connection(db_path)
            if _is_postgres():
                with conn.cursor() as cur:
                    cur.execute("SELECT name_lower, region FROM colleges")
                    rows = cur.fetchall()
                _region_cache = {r["name_lower"]: r["region"] for r in rows}
            else:
                rows = conn.execute("SELECT name_lower, region FROM colleges").fetchall()
                _region_cache = {r["name_lower"]: r["region"] for r in rows}
        except Exception:
            _region_cache = {}
    return _region_cache.get(college_name_lower.strip(), "Other")
