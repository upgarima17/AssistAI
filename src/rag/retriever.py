"""Embedding-based retrieval over the local IT knowledge base."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from config.config import CONFIG
from utils.config_loader import DATA_DIR

_INDEX_LOCK = threading.Lock()
_VECTOR_STORE: FAISS | None = None
_VECTOR_STORE_KEY: tuple[str, str] | None = None


def _knowledge_base_path() -> Path:
    return DATA_DIR / "knowledge_base.json"


def _load_articles() -> list[dict[str, Any]]:
    return json.loads(_knowledge_base_path().read_text(encoding="utf-8"))


def _corpus_fingerprint() -> str:
    return hashlib.sha256(_knowledge_base_path().read_bytes()).hexdigest()


def _documents(articles: list[dict[str, Any]]) -> list[Document]:
    return [
        Document(
            page_content="\n".join([
                article["title"],
                "Keywords: " + ", ".join(article["keywords"]),
                article["content"],
            ]),
            metadata={
                "id": article["id"],
                "title": article["title"],
                "keywords": article["keywords"],
                "content": article["content"],
            },
        )
        for article in articles
    ]


def _embedding_model_name() -> str:
    return os.getenv("OPENAI_EMBEDDING_MODEL", str(CONFIG["rag"]["embedding_model"]))


def _index_directory() -> Path:
    return Path(str(CONFIG["rag"]["index_dir"]))


def _score_threshold() -> float:
    return float(os.getenv("RAG_SCORE_THRESHOLD", CONFIG["rag"]["score_threshold"]))


def _get_vector_store() -> FAISS:
    global _VECTOR_STORE, _VECTOR_STORE_KEY

    key = (_corpus_fingerprint(), _embedding_model_name())
    with _INDEX_LOCK:
        if _VECTOR_STORE is not None and _VECTOR_STORE_KEY == key:
            return _VECTOR_STORE

        index_directory = _index_directory()
        index_file = index_directory / "index.faiss"
        metadata_file = index_directory / "metadata.json"
        embeddings = OpenAIEmbeddings(model=key[1])

        if index_file.exists() and metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            if metadata == {"corpus": key[0], "embedding_model": key[1]}:
                _VECTOR_STORE = FAISS.load_local(
                    str(index_directory),
                    embeddings,
                    allow_dangerous_deserialization=True,
                )
                _VECTOR_STORE_KEY = key
                return _VECTOR_STORE

        articles = _load_articles()
        index_directory.mkdir(parents=True, exist_ok=True)
        _VECTOR_STORE = FAISS.from_documents(_documents(articles), embeddings)
        _VECTOR_STORE.save_local(str(index_directory))
        metadata_file.write_text(
            json.dumps({"corpus": key[0], "embedding_model": key[1]}),
            encoding="utf-8",
        )
        _VECTOR_STORE_KEY = key
        return _VECTOR_STORE


def _reset_cache() -> None:
    """Reset the process-local index cache for tests and controlled reloads."""
    global _VECTOR_STORE, _VECTOR_STORE_KEY
    with _INDEX_LOCK:
        _VECTOR_STORE = None
        _VECTOR_STORE_KEY = None


def retrieve(query: str, limit: int = 3) -> list[dict[str, Any]]:
    if limit <= 0 or not query.strip():
        return []

    vector_store = _get_vector_store()
    matches = vector_store.similarity_search_with_score(query, k=limit)
    return [
        {
            **document.metadata,
            "source": document.metadata["id"],
            "score": float(score),
        }
        for document, score in matches
        if float(score) <= _score_threshold()
    ]
