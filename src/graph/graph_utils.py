"""Reusable helper functions for the support graph."""

from __future__ import annotations

import re
from typing import Any, Mapping
import logging
from utils.llm import validate_generic_ticket_request_with_llm

logger = logging.getLogger(__name__)




# Objective: obtain the latest user message for graph processing.
# Input: graph state containing `user_query` or message history.
# Returns: the latest user message as text.
def latest_user_text(state: Mapping[str, Any]) -> str:
    """Read the current user request from direct state or message history."""
    return state.get("user_query") or state.get("messages", [])[-1].get("content", "")


# Objective: extract labeled software-request fields from a query.
# Input: user query containing application, business reason, or device labels.
# Returns: a dictionary containing only the fields found in the query.
def parse_software_request(query: str) -> dict[str, str]:
    """Extract labeled software-request fields from a user query."""
    fields: dict[str, str] = {}
    field_patterns = {
        "application_name": r"application(?: name)?\s*[:=-]\s*(.+?)(?=\s*(?:business reason|device(?: name)?)\s*[:=-]|$)",
        "business_reason": r"business reason\s*[:=-]\s*(.+?)(?=\s*(?:application(?: name)?|device(?: name)?)\s*[:=-]|$)",
        "device_name": r"device(?: name)?\s*[:=-]\s*(.+?)(?=\s*(?:application(?: name)?|business reason)\s*[:=-]|$)",
    }
    for field, pattern in field_patterns.items():
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            fields[field] = match.group(1).strip(" \t,;.")
    return fields


# Objective: detect requests that ask for a ticket without describing an issue.
# Input: the user's ticket-related query.
# Returns: True for a detail-free request; otherwise False.
def is_generic_ticket_request(query: str) -> bool:
    """Identify ticket requests that provide no issue details.

    Fails CLOSED: if the LLM fallback errors, we treat the request as
    generic (ask for clarification) rather than risk creating a junk ticket.
    """
    normalized = re.sub(r"[^a-z0-9']+", " ", query.lower()).strip()
    if not normalized:
        return True

    generic_pattern = (
        r"^(?:(?:please|can you|could you|would you|help me|want to|need to|i want to|i need to|"
        r"i want|i need|i'd like to|i would like to)\s+)?"
        r"(?:(?:create|open|raise|make|submit|file|log|report|request)\s+)?"
        r"(?:(?:a|an|another|new)\s+){0,2}(?:support\s+)?"
        r"(?:ticket|incident|request)(?:\s+for me)?$"
    )
    need_or_want_ticket_pattern = (
        r"^(?:(?:i|we)\s+)?(?:need|want|would like)\s+"
        r"(?:(?:a|an|another|new)\s+){0,2}(?:support\s+)?"
        r"(?:ticket|incident|request)$"
    )
    if re.fullmatch(generic_pattern, normalized) or re.fullmatch(need_or_want_ticket_pattern, normalized):
        return True

    try:
        return validate_generic_ticket_request_with_llm(query)
    except Exception:
        logger.warning(
            "generic-request LLM check failed for query=%r; defaulting to generic",
            query,
            exc_info=True,
        )
        return True  # fail closed: ask for clarification rather than risk a junk ticket




def is_fresh_ticket_request(query: str) -> bool:
    """Identify an explicit request to start a separate ticket draft."""
    normalized = re.sub(r"[^a-z0-9']+", " ", query.lower()).strip()
    return bool(re.search(r"\b(?:new|another|separate)\s+(?:support\s+)?(?:ticket|incident|request)\b", normalized))


# Objective: recover ticket details supplied in an earlier conversation turn.
# Input: graph state containing prior user and assistant messages.
# Returns: previously labeled title and problem fields, or an empty dictionary.
def previous_ticket_context(state: Mapping[str, Any]) -> dict[str, str]:
    """Recover explicit title and problem details from earlier user messages."""
    messages = state.get("messages", [])
    for message in reversed(messages[:-1]):
        if message.get("role") != "user":
            continue
        content = message.get("content", "").strip()
        problem_match = re.search(r"\bproblem\s*:\s*(.+?)(?:\s*$)", content, re.IGNORECASE)
        if problem_match:
            title_match = re.search(r"\btitle\s*:\s*(.+?)(?:\s+problem\s*:|$)", content, re.IGNORECASE)
            return {
                "ticket_title": title_match.group(1).strip(" ;.") if title_match else "",
                "ticket_problem": problem_match.group(1).strip(" ;."),
            }
    return {}


# Objective: identify a vague confirmation that adds no new issue details.
# Input: the user's latest follow-up query.
# Returns: True when the follow-up only confirms the existing issue; otherwise False.
def is_vague_ticket_follow_up(query: str) -> bool:
    """Identify confirmations that do not add a new issue description."""
    normalized = re.sub(r"[^a-z0-9']+", " ", query.lower()).strip()
    if normalized in {
        "still not working", "not working", "still broken", "same issue",
        "same problem", "it is still not working", "it still does not work",
    }:
        return True
    return bool(re.fullmatch(r"(?:still )?(?:not working|broken) (?:create|open|raise) (?:a )?ticket", normalized))
