"""SQLite connection and schema management."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from utils.config_loader import DATA_DIR

DATABASE_PATH = DATA_DIR / "AssistIQ.sqlite3"
LEGACY_TICKETS_PATH = DATA_DIR / "tickets.json"
LEGACY_EMPLOYEES_PATH = DATA_DIR / "employees.json"


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


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)
        ticket_count = connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        if ticket_count == 0 and LEGACY_TICKETS_PATH.exists():
            tickets = json.loads(LEGACY_TICKETS_PATH.read_text(encoding="utf-8"))
            connection.executemany(
                """INSERT OR IGNORE INTO tickets
                (ticket_id, employee_id, title, description, status, priority, created_at)
                VALUES (:ticket_id, :employee_id, :title, :description, :status, :priority, :created_at)""",
                [
                    {**ticket, "created_at": ticket.get("created_at", "")}
                    for ticket in tickets
                ],
            )
        employee_count = connection.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        if employee_count == 0 and LEGACY_EMPLOYEES_PATH.exists():
            employees = json.loads(LEGACY_EMPLOYEES_PATH.read_text(encoding="utf-8"))
            connection.executemany(
                """INSERT OR IGNORE INTO employees (employee_id, name, department)
                VALUES (:employee_id, :name, :department)""",
                employees,
            )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


initialize_database()
