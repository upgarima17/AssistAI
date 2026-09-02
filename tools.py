"""Local tools used by the IT support graph."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"


def _read_json(filename: str) -> list[dict[str, Any]]:
    with (DATA_DIR / filename).open(encoding="utf-8") as file:
        return json.load(file)


def _write_json(filename: str, records: list[dict[str, Any]]) -> None:
    with (DATA_DIR / filename).open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)
        file.write("\n")


@tool
def knowledge_search(query: str) -> dict[str, Any]:
    """Search the local IT knowledge base for troubleshooting guidance."""
    terms = set(query.lower().split())
    matches = []
    for article in _read_json("knowledge_base.json"):
        haystack = " ".join([article["title"], article["content"], *article["keywords"]]).lower()
        score = sum(term in haystack for term in terms)
        if score:
            matches.append((score, article))
    matches.sort(key=lambda item: item[0], reverse=True)
    return {"matches": [article for _, article in matches[:3]], "query": query}


@tool
def ticket_lookup(employee_id: str, ticket_id: str = "", query: str = "") -> dict[str, Any]:
    """Find existing local support tickets for an employee or ticket ID."""
    tickets = _read_json("tickets.json")
    normalized_id = ticket_id.strip().upper()
    normalized_query = query.strip().lower()
    matches = [
        ticket for ticket in tickets
        if (employee_id and ticket["employee_id"].upper() == employee_id.strip().upper())
        or (normalized_id and ticket["ticket_id"].upper() == normalized_id)
        or (normalized_query and normalized_query in ticket["title"].lower())
    ]
    return {"matches": matches, "employee_id": employee_id, "ticket_id": normalized_id}


@tool
def ticket_create(employee_id: str, title: str, description: str, priority: str = "Medium") -> dict[str, Any]:
    """Create a support ticket in the local JSON ticket store."""
    employee_id = employee_id.strip().upper()
    title = title.strip()
    description = description.strip()
    priority = priority.strip().title() or "Medium"
    if not employee_id or not title or not description:
        return {"created": False, "error": "employee_id, title, and description are required"}

    tickets = _read_json("tickets.json")
    duplicate = next(
        (ticket for ticket in tickets
         if ticket["employee_id"] == employee_id
         and ticket["title"].lower() == title.lower()
         and ticket["status"] not in {"Resolved", "Closed"}),
        None,
    )
    if duplicate:
        return {"created": False, "duplicate": duplicate}

    next_number = max((int(ticket["ticket_id"].split("-")[1]) for ticket in tickets), default=1000) + 1
    ticket = {
        "ticket_id": f"INC-{next_number}",
        "employee_id": employee_id,
        "title": title,
        "description": description,
        "status": "New",
        "priority": priority,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    tickets.append(ticket)
    _write_json("tickets.json", tickets)
    return {"created": True, "ticket": ticket}
