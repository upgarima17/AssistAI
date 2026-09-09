import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit.client as client


def test_api_url_uses_env_override_without_trailing_slash(monkeypatch):
    monkeypatch.setenv("ASSISTAI_API_URL", "https://backend.example.com/")
    monkeypatch.delenv("BACKEND_API_URL", raising=False)
    importlib.reload(client)
    assert client.API_URL == "https://backend.example.com"


def test_api_url_falls_back_to_backend_env(monkeypatch):
    monkeypatch.delenv("ASSISTAI_API_URL", raising=False)
    monkeypatch.setenv("BACKEND_API_URL", "https://backend.example.com")
    importlib.reload(client)
    assert client.API_URL == "https://backend.example.com"
