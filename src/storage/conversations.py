"""SQLite persistence for graph state and chat messages."""

from __future__ import annotations

import json
from typing import Any

from .database import get_connection


def load_state(thread_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT state_json FROM conversations WHERE thread_id = ?", (thread_id,)
        ).fetchone()
    return json.loads(row[0]) if row else {"messages": []}


def save_state(thread_id: str, state: dict[str, Any]) -> None:
    employee_id = state.get("employee_id")
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO conversations(thread_id, employee_id, state_json)
               VALUES (?, ?, ?)
               ON CONFLICT(thread_id) DO UPDATE SET
                 employee_id = excluded.employee_id,
                 state_json = excluded.state_json,
                 updated_at = CURRENT_TIMESTAMP""",
            (thread_id, employee_id, json.dumps(state)),
        )
        connection.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
        connection.executemany(
            "INSERT INTO messages(thread_id, role, content) VALUES (?, ?, ?)",
            [(thread_id, message["role"], message["content"]) for message in state.get("messages", [])],
        )
