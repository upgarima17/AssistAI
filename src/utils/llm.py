"""Optional LLM integration used by the response-generation node."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any, Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from utils.config_loader import CONFIG

load_dotenv()

# llm loader 
@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI | None:
    """Return the configured chat model, or None for offline mode."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    llm_config = CONFIG.get("llm", {})
    return ChatOpenAI(
        model=llm_config.get("openai_model") or "gpt-4o-mini",
        temperature=llm_config.get("temperature", 0),
        api_key=api_key,
    )


def validate_generic_ticket_request_with_llm(query: str) -> bool:
    """Use the configured LLM to validate whether a request lacks issue details."""
    llm = get_llm()
    if llm is None:
        return False

    prompt = [
        {
            "role": "system",
            "content": (
                "Analyze the user's IT support query. Reply with 'true' if the user is merely asking "
                "to open/create/raise a ticket without providing any actual technical details or symptoms. "
                "Reply with 'false' if they describe a specific problem (e.g., broken screen, VPN issues, slow PC).\n"
                "Output ONLY 'true' or 'false'."
            ),
        },
        {"role": "user", "content": query},
    ]
    try:
        response = llm.invoke(prompt)
        return response.content.strip().lower() == "true"
    except Exception:
        return False


# This helper is the single boundary for structured ticket extraction. Keeping
# model creation, schema binding, invocation, and failure handling here keeps
# graph.py focused on workflow decisions and lets the application continue in
# deterministic offline mode when an API key or model response is unavailable.
def extract_structured_ticket_details_with_llm(
    query: str,
    output_schema: type[BaseModel],
) -> BaseModel | None:
    """Extract structured ticket details using the configured LLM."""
    llm = get_llm()
    if llm is None:
        return None

    try:
        structured_llm = llm.with_structured_output(output_schema)
        return structured_llm.invoke(f"Extract ticket details from this user request: {query}")
    except Exception:
        return None

class IntentRouterOutput(BaseModel):
    """Schema to force the LLM to choose a strict valid graph route."""
    route: Literal["knowledge", "lookup", "create", "clarify"] = Field(
        description="The matching target route for the support request."
    )


def classify_intent_with_llm(user_query: str) -> str | None:
    """Classify a request into a graph route when an LLM is configured."""
    llm = get_llm()
    if llm is None:
        return None

    # Force ChatOpenAI to yield a validated Pydantic object instead of a text message
    try:
        structured_llm = llm.with_structured_output(IntentRouterOutput)
    except Exception:
        return None

    prompt = [
        {
            "role": "system",
            "content": (
                "Classify the IT support request into exactly one route:\n"
                "- knowledge: for troubleshooting, questions, or how-to help.\n"
                "- lookup: for checking status, viewing, or searching an existing ticket/incident.\n"
                "- create: for opening, raising, reporting a new problem, or requesting a new ticket.\n"
                "- clarify: for requests that are ambiguous, generic greetings, or do not fit the other routes."
            ),
        },
        {"role": "user", "content": user_query},
    ]

    try:
        # result is now an instance of IntentRouterOutput
        result = structured_llm.invoke(prompt)
        return result.route
    except Exception:
        # Fall back to None so your main node gracefully resorts to 'clarify'
        return None

# llm response generator
def generate_grounded_response(
    *,
    user_query: str,
    intent: str,
    tool_result: dict[str, Any],
    sources: list[str],
) -> str | None:
    """Generate a response using only the verified result from a local tool.

    Returning None lets the graph use its deterministic offline response when
    no API key is configured or the model is temporarily unavailable.
    """
    llm = get_llm()
    if llm is None:
        return None

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an IT support assistant. Answer using only the supplied tool result. "
                "Do not invent ticket IDs, statuses, employee details, or troubleshooting steps. "
                "If the result is empty, say that no reliable information was found. "
                "Be concise and friendly. Mention source IDs when sources are provided."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "request": user_query,
                    "intent": intent,
                    "tool_result": tool_result,
                    "sources": sources,
                },
                default=str,
            ),
        },
    ]
    try:
        result = llm.invoke(prompt);
        print("LLM result:", result);
    except Exception:
        return None

    content = result.content
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None
