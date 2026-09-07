"""Database connection, schema management, and seed data."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except ModuleNotFoundError:
    psycopg = None
    dict_row = None

from utils.config_loader import DATA_DIR

DATABASE_PATH = DATA_DIR / "assistai.sqlite3"
DATABASE_URL = os.getenv("DATABASE_URL")
TICKETS_SEED_PATH = DATA_DIR / "tickets_example.json"
EMPLOYEES_SEED_PATH = DATA_DIR / "employees_example.json"


SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_employee ON tickets(employee_id);
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    thread_id TEXT PRIMARY KEY,
    employee_id TEXT,
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(thread_id) REFERENCES conversations(thread_id)
);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id, id);
"""


POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_employee ON tickets(employee_id);
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    thread_id TEXT PRIMARY KEY,
    employee_id TEXT,
    state_json TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES conversations(thread_id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id, id);
"""


def using_postgres() -> bool:
    return bool(DATABASE_URL)


def get_connection() -> Any:
    if using_postgres():
        if psycopg is None or dict_row is None:
            raise RuntimeError("Install psycopg[binary] to use DATABASE_URL.")
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        if using_postgres():
            for statement in POSTGRES_SCHEMA.split(";"):
                statement = statement.strip()
                if statement:
                    connection.execute(statement)
        else:
            connection.executescript(SCHEMA)
        ticket_count_row = connection.execute("SELECT COUNT(*) AS count FROM tickets").fetchone()
        ticket_count = ticket_count_row["count"] if using_postgres() else ticket_count_row[0]
        if ticket_count == 0 and TICKETS_SEED_PATH.exists():
            tickets = json.loads(TICKETS_SEED_PATH.read_text(encoding="utf-8"))
            ticket_rows = [
                {
                    **ticket,
                    "created_at": ticket.get("created_at") or datetime.now(timezone.utc).isoformat(),
                }
                for ticket in tickets
            ]
            if using_postgres():
                connection.executemany(
                    """INSERT INTO tickets
                    (ticket_id, employee_id, title, description, status, priority, created_at)
                    VALUES (%(ticket_id)s, %(employee_id)s, %(title)s, %(description)s,
                            %(status)s, %(priority)s, %(created_at)s)
                    ON CONFLICT (ticket_id) DO NOTHING""",
                    ticket_rows,
                )
            else:
                connection.executemany(
                    """INSERT OR IGNORE INTO tickets
                    (ticket_id, employee_id, title, description, status, priority, created_at)
                    VALUES (:ticket_id, :employee_id, :title, :description, :status, :priority, :created_at)""",
                    ticket_rows,
                )
        employee_count_row = connection.execute("SELECT COUNT(*) AS count FROM employees").fetchone()
        employee_count = employee_count_row["count"] if using_postgres() else employee_count_row[0]
        if employee_count == 0 and EMPLOYEES_SEED_PATH.exists():
            employees = json.loads(EMPLOYEES_SEED_PATH.read_text(encoding="utf-8"))
            if using_postgres():
                connection.executemany(
                    """INSERT INTO employees (employee_id, name, department)
                    VALUES (%(employee_id)s, %(name)s, %(department)s)
                    ON CONFLICT (employee_id) DO NOTHING""",
                    employees,
                )
            else:
                connection.executemany(
                    """INSERT OR IGNORE INTO employees (employee_id, name, department)
                    VALUES (:employee_id, :name, :department)""",
                    employees,
                )


def row_to_dict(row: Any | None) -> dict[str, Any] | None:
    return dict(row) if row else None


initialize_database()
