"""FastAPI HTTP interface for the local IT support graph."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from graph.graph import SupportState, support_graph
from storage.conversations import load_state, save_state


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
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    thread_id = request.thread_id or str(uuid4())
    state = load_state(thread_id)
    messages = [*state.get("messages", []), {"role": "user", "content": request.message}]
    graph_state: SupportState = {**state, "messages": messages, "user_query": request.message}
    if request.employee_id:
        graph_state["employee_id"] = request.employee_id.strip().upper()

    try:
        result = support_graph.invoke(graph_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="The support workflow failed.") from exc

    response = result.get("response")
    if not response:
        raise HTTPException(status_code=500, detail="The support workflow returned no response.")
    save_state(thread_id, {**result, "messages": [*messages, {"role": "assistant", "content": response}]})
    return ChatResponse(thread_id=thread_id, response=response, intent=result.get("intent", "clarify"), sources=result.get("sources", []))
