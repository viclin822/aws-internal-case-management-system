import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE = os.getenv("DATABASE_PATH", "database.db")

schema_sql = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('submitter', 'agent', 'admin')),
    department TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT '中' CHECK (priority IN ('低', '中', '高')),
    student_account TEXT NOT NULL,
    student_name TEXT,
    teacher_name TEXT,
    department TEXT,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '待處理' CHECK (status IN ('待處理', '處理中', '待追蹤', '已結案')),
    submitter_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (submitter_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS case_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS case_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    comment TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS case_status_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT,
    changed_by INTEGER,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id)
);
"""

try:
    conn = sqlite3.connect(DATABASE)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    print(f"資料表建立完成：{DATABASE}")
except Exception as e:
    print(f"建立資料表失敗：{e}")