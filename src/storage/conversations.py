"""SQLite persistence for graph state and chat messages."""

from __future__ import annotations

import json
from typing import Any

from .database import get_connection, using_postgres


def load_state(thread_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        placeholder = "%s" if using_postgres() else "?"
        row = connection.execute(
            f"SELECT state_json FROM conversations WHERE thread_id = {placeholder}",
            (thread_id,),
        ).fetchone()
    return json.loads(row["state_json"] if using_postgres() else row[0]) if row else {"messages": []}


def save_state(thread_id: str, state: dict[str, Any]) -> None:
    employee_id = state.get("employee_id")
    with get_connection() as connection:
        if using_postgres():
            connection.execute(
                """INSERT INTO conversations(thread_id, employee_id, state_json)
                   VALUES (%s, %s, %s)
                   ON CONFLICT(thread_id) DO UPDATE SET
                     employee_id = excluded.employee_id,
                     state_json = excluded.state_json,
                     updated_at = CURRENT_TIMESTAMP""",
                (thread_id, employee_id, json.dumps(state)),
            )
            connection.execute("DELETE FROM messages WHERE thread_id = %s", (thread_id,))
        else:
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
            "INSERT INTO messages(thread_id, role, content) VALUES (%s, %s, %s)"
            if using_postgres()
            else "INSERT INTO messages(thread_id, role, content) VALUES (?, ?, ?)",
            [(thread_id, message["role"], message["content"]) for message in state.get("messages", [])],
        )
