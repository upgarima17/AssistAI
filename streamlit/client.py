"""HTTP client for the AssistIQ FastAPI service."""

from __future__ import annotations

import os
from typing import Any

import requests


API_URL = (
    os.getenv("ASSISTAI_API_URL")
    or os.getenv("BACKEND_API_URL")
    or "http://127.0.0.1:8000"
).rstrip("/")


def send_message(message: str, thread_id: str | None, employee_id: str) -> dict[str, Any]:
    payload = {"message": message, "thread_id": thread_id, "employee_id": employee_id or None}
    response = requests.post(f"{API_URL}/chat", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()
