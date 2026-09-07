"""FastAPI HTTP interface for the local IT support graph."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from graph.graph import SupportState, support_graph
from storage.conversations import load_state, save_state
from storage.database import get_connection


logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="The employee's latest support request")
    thread_id: str | None = Field(default=None, description="Thread ID from an earlier request")
    employee_id: str | None = Field(default=None, description="Employee ID, such as EMP1024")


class ChatResponse(BaseModel):
    thread_id: str
    response: str
    intent: str
    sources: list[str] = Field(default_factory=list)


app = FastAPI(title="AssistIQ IT Support API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        thread_id = request.thread_id or str(uuid4())
        state = load_state(thread_id)
        messages = [*state.get("messages", []), {"role": "user", "content": request.message}]
        graph_state: SupportState = {**state, "messages": messages, "user_query": request.message}
        if request.employee_id:
            graph_state["employee_id"] = request.employee_id.strip().upper()

        result = support_graph.invoke(graph_state)
        response = result.get("response")
        if not response:
            raise RuntimeError("The support workflow returned no response.")
        save_state(thread_id, {**result, "messages": [*messages, {"role": "assistant", "content": response}]})
    except Exception as exc:
        logger.exception("Support request failed")
        raise HTTPException(status_code=500, detail="The support workflow failed.") from exc
    return ChatResponse(thread_id=thread_id, response=response, intent=result.get("intent", "clarify"), sources=result.get("sources", []))
