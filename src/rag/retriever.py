"""Local knowledge retrieval boundary.

The initial implementation uses lightweight lexical retrieval. Its result shape is
intentionally compatible with a future embedding/vector-store retriever.
"""

from __future__ import annotations

import json
import re
from typing import Any

from utils.config_loader import DATA_DIR



def retrieve(query: str, limit: int = 3) -> list[dict[str, Any]]:
    stop_words = {"a", "an", "and", "do", "how", "i", "is", "my", "of", "the", "to", "what", "your"}
    terms = {term for term in re.findall(r"[a-z0-9]+", query.lower()) if term not in stop_words}
    articles = json.loads((DATA_DIR / "knowledge_base.json").read_text(encoding="utf-8"))
    ranked: list[tuple[int, dict[str, Any]]] = []
    for article in articles:
        searchable = " ".join([article["title"], article["content"], *article["keywords"]]).lower()
        score = sum(term in searchable for term in terms)
        if score:
            ranked.append((score, {**article, "source": article["id"], "score": score}))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [article for _, article in ranked[:limit]]
