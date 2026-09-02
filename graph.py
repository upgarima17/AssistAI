"""LangGraph workflow for the local IT support assistant."""

from __future__ import annotations

import os
import re
from typing import Any, Literal
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from tools import knowledge_search, ticket_create, ticket_lookup


class SupportState(TypedDict, total=False):
    messages: list[dict[str, str]]
    user_query: str
    employee_id: str
    intent: Literal["knowledge", "lookup", "create", "clarify"]
    ticket_title: str
    ticket_description: str
    tool_result: dict[str, Any]
    response: str
    error: str


def _latest_user_text(state: SupportState) -> str:
    return state.get("user_query") or state.get("messages", [])[-1].get("content", "")


def decide_intent(state: SupportState) -> dict[str, Any]:
    query = _latest_user_text(state)
    lowered = query.lower()
    employee_match = re.search(r"\bemp\s?-?\d{4}\b", query, re.IGNORECASE)
    updates: dict[str, Any] = {"user_query": query}
    if employee_match:
        updates["employee_id"] = employee_match.group(0).replace(" ", "").upper()

    if any(word in lowered for word in ("create", "raise", "open", "report", "new ticket")):
        updates["intent"] = "create"
    elif any(word in lowered for word in ("status", "ticket", "incident", "existing")):
        updates["intent"] = "lookup"
    elif any(word in lowered for word in ("how", "reset", "connect", "install", "fix", "vpn", "wifi", "wi-fi")):
        updates["intent"] = "knowledge"
    else:
        updates["intent"] = "clarify"
    return updates


def route(state: SupportState) -> str:
    return state.get("intent", "clarify")


def run_knowledge_search(state: SupportState) -> dict[str, Any]:
    return {"tool_result": knowledge_search.invoke({"query": _latest_user_text(state)})}


def run_ticket_lookup(state: SupportState) -> dict[str, Any]:
    employee_id = state.get("employee_id", "")
    if not employee_id:
        return {"error": "I need your employee ID (for example, EMP1024) before I can look up tickets."}
    return {"tool_result": ticket_lookup.invoke({"employee_id": employee_id, "query": _latest_user_text(state)})}


def run_ticket_creation(state: SupportState) -> dict[str, Any]:
    employee_id = state.get("employee_id", "")
    query = _latest_user_text(state)
    if not employee_id:
        return {"error": "Before I create a ticket, please provide your employee ID (for example, EMP1024)."}
    title = state.get("ticket_title") or query[:80]
    description = state.get("ticket_description") or query
    request_only = {
        "please raise a ticket",
        "raise a ticket",
        "create a ticket",
        "open a ticket",
    }
    if len(description.strip()) < 10 or query.strip().lower() in request_only:
        return {"error": "Please describe the IT problem in a little more detail before I create the ticket."}
    return {"tool_result": ticket_create.invoke({"employee_id": employee_id, "title": title, "description": description})}


def generate_response(state: SupportState) -> dict[str, str]:
    if state.get("error"):
        return {"response": state["error"]}
    result = state.get("tool_result", {})
    intent = state.get("intent")
    if intent == "clarify":
        return {"response": "I can search IT guidance, check an existing ticket, or create a new ticket. What would you like to do?"}
    if intent == "knowledge":
        matches = result.get("matches", [])
        if not matches:
            return {"response": "I could not find a matching knowledge-base article. I can create a ticket if you describe the issue."}
        article = matches[0]
        return {"response": f"**{article['title']}** ({article['id']})\n\n{article['content']}"}
    if intent == "lookup":
        matches = result.get("matches", [])
        if not matches:
            return {"response": f"I found no tickets for {state.get('employee_id', 'that employee')}."}
        lines = [f"- **{item['ticket_id']}**: {item['title']} — {item['status']} ({item['priority']})" for item in matches]
        return {"response": "Here are the matching tickets:\n" + "\n".join(lines)}
    if result.get("duplicate"):
        duplicate = result["duplicate"]
        return {"response": f"A similar open ticket already exists: **{duplicate['ticket_id']}** ({duplicate['status']}). I did not create a duplicate."}
    if result.get("created"):
        ticket = result["ticket"]
        return {"response": f"Ticket **{ticket['ticket_id']}** created successfully. Status: **{ticket['status']}**; priority: **{ticket['priority']}**."}
    return {"response": "I could not complete that request because the local ticket tool returned no result."}


def build_graph():
    workflow = StateGraph(SupportState)
    workflow.add_node("decide", decide_intent)
    workflow.add_node("knowledge_search", run_knowledge_search)
    workflow.add_node("ticket_lookup", run_ticket_lookup)
    workflow.add_node("ticket_creation", run_ticket_creation)
    workflow.add_node("respond", generate_response)
    workflow.add_edge(START, "decide")
    workflow.add_conditional_edges("decide", route, {
        "knowledge": "knowledge_search",
        "lookup": "ticket_lookup",
        "create": "ticket_creation",
        "clarify": "respond",
    })
    workflow.add_edge("knowledge_search", "respond")
    workflow.add_edge("ticket_lookup", "respond")
    workflow.add_edge("ticket_creation", "respond")
    workflow.add_edge("respond", END)
    return workflow.compile()


support_graph = build_graph()
