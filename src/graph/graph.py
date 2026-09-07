"""LangGraph workflow for the local IT support assistant."""

from __future__ import annotations

import re
from typing import Any
from langgraph import graph
import logging
from langgraph.graph import END, START, StateGraph

from tools.tools import knowledge_search, ticket_create, ticket_lookup
from storage.employees import employee_exists
from storage.tickets import find_relevant_open_ticket
from graph.graph_utils import (
    is_generic_ticket_request,
    is_fresh_ticket_request,
    is_vague_ticket_follow_up,
    latest_user_text,
    parse_software_request,
    previous_ticket_context,
)
from graph.state import ExtractedTicketDetails, SupportState
from utils.llm import (
    classify_intent_with_llm,
    extract_structured_ticket_details_with_llm,
    generate_grounded_response,
)
logger = logging.getLogger(__name__)
# This graph node runs after intent routing but before ticket persistence. It
# converts natural language into the SupportState fields used by the creation
# node, allowing requests such as "my laptop screen will not turn on" to work
# even when the user does not use labels like "Device:" or "Problem:".
def extract_details_from_query(state: SupportState) -> dict[str, Any]:
    """Extract ticket fields from a naturally phrased request before creation."""
    if is_vague_ticket_follow_up(latest_user_text(state)):
        return {}
    extracted = extract_structured_ticket_details_with_llm(
        latest_user_text(state),
        ExtractedTicketDetails,
    )
    if extracted is None:
        return {}

    updates: dict[str, str] = {}
    for field in ("application_name", "business_reason", "device_name", "ticket_problem"):
        value = getattr(extracted, field, None)
        if value and value.strip():
            updates[field] = value.strip()
    return updates


# Graph node: classify the request and extract an employee ID when present.
def decide_intent(state: SupportState) -> dict[str, Any]:
    query = latest_user_text(state).strip()
    lowered = query.lower()
    software_request = parse_software_request(query)
    employee_match = re.fullmatch(r"emp\s*-?\s*\d{4}", query, re.IGNORECASE)

    updates: dict[str, Any] = {
        "user_query": query,
        "error": "",
        "tool_result": {},
        "sources": [],
    }
    updates.update(software_request)

    # 1. Handle Employee ID logic first
    if employee_match:
        updates["employee_id"] = re.sub(r"[\s-]", "", employee_match.group(0)).upper()
        previous_intent = state.get("intent")
        if previous_intent in {"lookup", "create"}:
            updates["intent"] = previous_intent
            return updates  # Immediate return for ID confirmation

    # 2. Pure Logic / Keyword Check
    creation_request = re.search(
        r"\b(?:create|open|raise|make|submit|file|log|report|request)\b.*\b(?:ticket|incident|request|issue)\b",
        lowered,
    )
    action_only_creation = any(
        phrase in lowered
        for phrase in ("new ticket", "new incident", "new request", "need a ticket", "want a ticket")
    )
    if software_request or creation_request or action_only_creation:
        updates["intent"] = "create"
        if is_fresh_ticket_request(query):
            updates.update({
                "ticket_title": "",
                "ticket_description": "",
                "ticket_problem": "",
                "application_name": "",
                "business_reason": "",
                "device_name": "",
            })
    elif any(word in lowered for word in ("status", "ticket", "incident", "existing")):
        updates["intent"] = "lookup"
    elif any(word in lowered for word in ("how", "reset", "connect", "install", "fix", "vpn", "wifi", "wi-fi")):
        updates["intent"] = "knowledge"
    else:
        updates["intent"] = "clarify"

    # 3. LLM Fallback (Only runs if keywords resulted in "clarify")
    if updates["intent"] == "clarify":
        try:
            llm_intent = classify_intent_with_llm(query)
        except Exception:
            logger.warning("intent classification LLM call failed for query=%r", query, exc_info=True)
            llm_intent = None
        if llm_intent in {"create", "lookup", "knowledge"}:
            updates["intent"] = llm_intent
        # If LLM also fails or returns something invalid, it safely stays "clarify"

    logger.info('intent classification result: %s', updates["intent"])
    return updates



# Route to the node selected by the intent classifier.
def route(state: SupportState) -> str:
    return state.get("intent", "clarify")


# Graph node: search the local knowledge base and collect source IDs.
def run_knowledge_search(state: SupportState) -> dict[str, Any]:
    result = knowledge_search.invoke({"query": latest_user_text(state)})
    return {"tool_result": result, "sources": [item["source"] for item in result.get("matches", [])]}


# Graph node: validate the employee and look up matching support tickets.
def run_ticket_lookup(state: SupportState) -> dict[str, Any]:
    employee_id = state.get("employee_id", "")
    if not employee_id:
        return {"error": "I need your employee ID (for example, EMP1024) before I can look up tickets."}
    if not employee_exists(employee_id):
        return {"error": f"I could not verify {employee_id}. Please check your employee ID and try again."}
    return {"tool_result": ticket_lookup.invoke({"employee_id": employee_id, "query": latest_user_text(state)})}


# Graph node: validate the request and create a new support ticket.
def run_ticket_creation(state: SupportState) -> dict[str, Any]:
    employee_id = state.get("employee_id", "")
    query = latest_user_text(state)
    software_request = parse_software_request(query)
    generic_ticket_request = is_generic_ticket_request(query)

    if not employee_id:
        return {"error": "Before I create a ticket, please provide your employee ID (for example, EMP1024)."}
    if not employee_exists(employee_id):
        return {"error": f"I could not verify {employee_id}. Please check your employee ID before creating a ticket."}

    software_fields = {
        "application_name": state.get("application_name", "").strip() or software_request.get("application_name", "").strip(),
        "business_reason": state.get("business_reason", "").strip() or software_request.get("business_reason", "").strip(),
        "device_name": state.get("device_name", "").strip() or software_request.get("device_name", "").strip(),
    }
    software_request_started = bool(
        software_fields["application_name"] or software_fields["business_reason"]
    )
    if software_request_started and not all(software_fields.values()):
        return {"error": "To request software, provide all three fields in this format: Application: <name>; Business reason: <reason>; Device: <device name>."}

    if software_request_started and all(software_fields.values()):
        problem = f"Software installation request for {software_fields['application_name']}"
        title = f"Software installation: {software_fields['application_name']}"
        description = (
            f"Application: {software_fields['application_name']}\n"
            f"Business reason: {software_fields['business_reason']}\n"
            f"Device: {software_fields['device_name']}"
        )
        duplicate = find_relevant_open_ticket(employee_id, problem)
        if duplicate:
            return {"ticket_problem": problem, "ticket_title": title, "ticket_description": description, "tool_result": {"created": False, "duplicate": duplicate}}
        return {
            "ticket_problem": problem,
            "ticket_title": title,
            "ticket_description": description,
            "tool_result": ticket_create.invoke({"employee_id": employee_id, "title": title, "description": description}),
        }

    problem = state.get("ticket_problem", "").strip()
    title = state.get("ticket_title", "").strip()
    prior_context = previous_ticket_context(state)

    if not problem and is_vague_ticket_follow_up(query):
        problem = prior_context.get("ticket_problem", "")
        title = prior_context.get("ticket_title", "")

    # Fail-closed: only treat the raw query as the problem if it is
    # demonstrably NOT a bare intent statement. Default is to withhold,
    # not to accept.
    if not problem and not is_vague_ticket_follow_up(query):
        candidate = query.strip()
        if not is_generic_ticket_request(candidate) and len(candidate) >= 10:
            problem = candidate

    if len(problem) < 10 or is_generic_ticket_request(problem) or (generic_ticket_request and not state.get("ticket_problem")):
        return {
            "error": "What problem are you experiencing?"
            " Please provide more detail in the format 'Title: <title>; Problem: <issue description>' or describe the issue in your own words."
        }

    title = title or problem.split(".", 1)[0][:80]
    description = state.get("ticket_description") or problem

    # Last-line-of-defense: never let a generic/empty title reach the tool call.
    if not title or is_generic_ticket_request(title) or len(title.split()) < 3:
        return {"error": "I still need a short description of the actual issue to create the ticket."}

    duplicate = find_relevant_open_ticket(employee_id, problem)
    if duplicate:
        return {
            "ticket_problem": problem,
            "ticket_title": title,
            "ticket_description": description,
            "tool_result": {"created": False, "duplicate": duplicate},
        }
    return {
        "ticket_problem": problem,
        "ticket_title": title,
        "ticket_description": description,
        "tool_result": ticket_create.invoke({"employee_id": employee_id, "title": title, "description": description}),
    }

# Graph node: generate an LLM response or use the deterministic offline fallback.
def generate_response(state: SupportState) -> dict[str, str]:
    if state.get("error"):
        return {"response": state["error"]}
    result = state.get("tool_result", {})
    intent = state.get("intent")
    llm_response = generate_grounded_response(
        user_query=latest_user_text(state),
        intent=intent or "clarify",
        tool_result=result,
        sources=state.get("sources", []),
    )
    if llm_response:
        return {"response": llm_response}
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


# Build and compile the LangGraph workflow and connect its nodes and routes.
def build_graph():
    workflow = StateGraph(SupportState)

    # Decide node: classify the user's request.
    workflow.add_node("decide", decide_intent)

    # Knowledge node: retrieve relevant local IT guidance.
    workflow.add_node("knowledge_search", run_knowledge_search)

    # Lookup node: find existing tickets for a verified employee.
    workflow.add_node("ticket_lookup", run_ticket_lookup)

    # Creation node: create a ticket after validation.
    workflow.add_node("extract_ticket_details", extract_details_from_query)
    workflow.add_node("ticket_creation", run_ticket_creation)

    # Response node: produce the final user-facing answer.
    workflow.add_node("respond", generate_response)
    workflow.add_edge(START, "decide")
    workflow.add_conditional_edges("decide", route, {
        "knowledge": "knowledge_search", "lookup": "ticket_lookup",
        "create": "extract_ticket_details", "clarify": "respond",
    })
    workflow.add_edge("extract_ticket_details", "ticket_creation")
    workflow.add_edge("knowledge_search", "respond")
    workflow.add_edge("ticket_lookup", "respond")
    workflow.add_edge("ticket_creation", "respond")
    workflow.add_edge("respond", END)
    return workflow.compile()


support_graph = build_graph()
