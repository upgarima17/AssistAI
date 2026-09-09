"""Employee lookup backed by the local SQLite database."""

from __future__ import annotations

from .database import get_connection, using_postgres


def employee_exists(employee_id: str) -> bool:
    normalized_id = employee_id.strip().upper()
    with get_connection() as connection:
        query = (
            "SELECT 1 FROM employees WHERE employee_id ILIKE %s"
            if using_postgres()
            else "SELECT 1 FROM employees WHERE employee_id = ? COLLATE NOCASE"
        )
        employee = connection.execute(
            query,
            (normalized_id,),
        ).fetchone()
    return employee is not None