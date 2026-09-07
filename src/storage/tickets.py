"""SQLite repository for support tickets."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from .database import get_connection, row_to_dict


def find_tickets(employee_id: str, ticket_id: str = "", query: str = "") -> list[dict[str, Any]]:
    normalized_employee = employee_id.strip().upper()
    normalized_ticket = ticket_id.strip().upper()
    query_value = f"%{query.strip()}%"
    with get_connection() as connection:
        rows = connection.execute(
                """SELECT * FROM tickets
                    WHERE (? != '' AND employee_id = ?)
                        OR (? != '' AND ticket_id = ?)
                        OR (? != '' AND title LIKE ? COLLATE NOCASE)
               ORDER BY created_at DESC""",
                (normalized_employee, normalized_employee, normalized_ticket, normalized_ticket, query.strip(), query_value),
        ).fetchall()
    return [dict(row) for row in rows]


def find_relevant_open_ticket(employee_id: str, problem: str) -> dict[str, Any] | None:
    """Find an open ticket for an employee that shares meaningful problem terms."""
    stop_words = {"about", "again", "and", "help", "issue", "please", "problem", "ticket", "the", "with"}
    problem_terms = {
        term for term in re.findall(r"[a-z0-9]+", problem.lower())
        if len(term) >= 4 and term not in stop_words
    }
    if not problem_terms:
        return None

    tickets = find_tickets(employee_id)
    for ticket in tickets:
        if ticket["status"] in {"Resolved", "Closed"}:
            continue
        ticket_terms = set(re.findall(r"[a-z0-9]+", f"{ticket['title']} {ticket['description']}".lower()))
        if problem_terms & ticket_terms:
            return ticket
    return None


def create_ticket(employee_id: str, title: str, description: str, priority: str = "Medium") -> dict[str, Any]:
    normalized_employee = employee_id.strip().upper()
    normalized_title = title.strip()
    normalized_description = description.strip()
    normalized_priority = priority.strip().title() or "Medium"
    if not normalized_employee or not normalized_title or not normalized_description:
        return {"created": False, "error": "employee_id, title, and description are required"}

    with get_connection() as connection:
        duplicate = connection.execute(
            """SELECT * FROM tickets
               WHERE employee_id = ? AND title = ? COLLATE NOCASE
                 AND status NOT IN ('Resolved', 'Closed')""",
            (normalized_employee, normalized_title),
        ).fetchone()
        if duplicate:
            return {"created": False, "duplicate": row_to_dict(duplicate)}

        next_number = connection.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(ticket_id, 5) AS INTEGER)), 1000) + 1 FROM tickets"
        ).fetchone()[0]
        ticket = {
            "ticket_id": f"INC-{next_number}",
            "employee_id": normalized_employee,
            "title": normalized_title,
            "description": normalized_description,
            "status": "New",
            "priority": normalized_priority,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        connection.execute(
            """INSERT INTO tickets
               (ticket_id, employee_id, title, description, status, priority, created_at)
               VALUES (:ticket_id, :employee_id, :title, :description, :status, :priority, :created_at)""",
            ticket,
        )
    return {"created": True, "ticket": ticket}
