CREATE TABLE IF NOT EXISTS colleges (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    name_lower TEXT    NOT NULL UNIQUE,
    lat        REAL,
    lng        REAL,
    region     TEXT    NOT NULL DEFAULT 'Other'
);

CREATE TABLE IF NOT EXISTS courses (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
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
    badges                TEXT    DEFAULT '[]',
    csu_breadth           TEXT    DEFAULT '[]',
    igetc                 TEXT    DEFAULT '[]',
    cal_getc              TEXT    DEFAULT '[]',
    professors            TEXT,
    units                 INTEGER,
    visible               INTEGER DEFAULT 1,
    filter_applied        INTEGER DEFAULT 1,
    course_notes          TEXT,
    seat_count            INTEGER,
    seats_available       INTEGER,
    seat_count_updated_at TEXT,
    source_file           TEXT
);

CREATE INDEX IF NOT EXISTS idx_courses_teaching_college ON courses(teaching_college);
CREATE INDEX IF NOT EXISTS idx_courses_start_date ON courses(start_date);
CREATE INDEX IF NOT EXISTS idx_courses_delivery_method ON courses(delivery_method);
