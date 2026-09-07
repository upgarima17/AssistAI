"""Local tools used by the IT support graph."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from rag.retriever import retrieve
from storage.tickets import create_ticket, find_tickets


@tool
def knowledge_search(query: str) -> dict[str, Any]:
    """Search the local IT knowledge base for troubleshooting guidance."""
    return {"matches": retrieve(query), "query": query}


@tool
def ticket_lookup(employee_id: str, ticket_id: str = "", query: str = "") -> dict[str, Any]:
    """Find existing local support tickets for an employee or ticket ID."""
    return {"matches": find_tickets(employee_id, ticket_id, query), "employee_id": employee_id, "ticket_id": ticket_id.strip().upper()}


@tool
def ticket_create(employee_id: str, title: str, description: str, priority: str = "Medium") -> dict[str, Any]:
    """Create a support ticket in the local SQLite ticket store."""
    return create_ticket(employee_id, title, description, priority)
