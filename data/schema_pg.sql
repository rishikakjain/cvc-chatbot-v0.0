-- PostgreSQL DDL for CVC course database (Aurora Serverless v2)
-- Run via migrate_to_postgres.py or psql directly.

CREATE TABLE IF NOT EXISTS colleges (
    id         SERIAL PRIMARY KEY,
    name       TEXT    NOT NULL UNIQUE,
    name_lower TEXT    NOT NULL UNIQUE,
    lat        DOUBLE PRECISION,
    lng        DOUBLE PRECISION,
    region     TEXT    NOT NULL DEFAULT 'Other'
);

CREATE TABLE IF NOT EXISTS courses (
    id                    SERIAL PRIMARY KEY,
    course_code           TEXT,
    course_name           TEXT,
    cid                   TEXT,
    section               TEXT,
    crn                   TEXT    UNIQUE,
    start_date            TEXT,
    end_date              TEXT,
    term                  TEXT,
    teaching_college      TEXT    REFERENCES colleges(name),
    delivery_method       TEXT,
    badges                JSONB   NOT NULL DEFAULT '[]',
    csu_breadth           JSONB   NOT NULL DEFAULT '[]',
    igetc                 JSONB   NOT NULL DEFAULT '[]',
    cal_getc              JSONB   NOT NULL DEFAULT '[]',
    professors            TEXT,
    units                 INTEGER,
    visible               BOOLEAN NOT NULL DEFAULT TRUE,
    filter_applied        BOOLEAN NOT NULL DEFAULT TRUE,
    course_notes          TEXT,
    seat_count            INTEGER,
    seats_available       INTEGER,
    seat_count_updated_at TEXT,
    source_file           TEXT
);

CREATE INDEX IF NOT EXISTS idx_courses_teaching_college ON courses(teaching_college);
CREATE INDEX IF NOT EXISTS idx_courses_start_date       ON courses(start_date);
CREATE INDEX IF NOT EXISTS idx_courses_delivery_method  ON courses(delivery_method);
