"""State schemas used by the support graph."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class SupportState(TypedDict, total=False):
	"""Runtime state passed between support graph nodes."""
	messages: list[dict[str, str]]
	user_query: str
	employee_id: str
	intent: Literal["knowledge", "lookup", "create", "clarify"]
	ticket_title: str
	ticket_description: str
	ticket_problem: str
	application_name: str
	business_reason: str
	device_name: str
	tool_result: dict[str, Any]
	response: str
	error: str
	sources: list[str]


class ExtractedTicketDetails(BaseModel):
	"""Structured fields extracted from a naturally phrased ticket request."""
	application_name: Optional[str] = Field(None, description="Name of the software application mentioned.")
	business_reason: Optional[str] = Field(None, description="The reason provided for the software request.")
	device_name: Optional[str] = Field(None, description="The computer, laptop, or device name.")
	ticket_problem: Optional[str] = Field(None, description="The technical issue or problem details, if provided.")
