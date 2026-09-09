import json
from pathlib import Path

import rag.retriever as retriever


class FakeEmbeddings:
    def __init__(self, model: str):
        self.model = model


class FakeVectorStore:
    def __init__(self, documents):
        self.documents = documents
        self.search_count = 0

    def save_local(self, directory):
        Path(directory, "index.faiss").write_text("fake", encoding="utf-8")

    def similarity_search_with_score(self, query, k):
        self.search_count += 1
        return [(document, float(index)) for index, document in enumerate(self.documents[:k])]


def test_retrieve_preserves_article_metadata_and_reuses_cached_store(monkeypatch, tmp_path):
    articles = [{
        "id": "KB-TEST",
        "title": "Test article",
        "keywords": ["test"],
        "content": "Test content",
    }]
    corpus = tmp_path / "knowledge_base.json"
    corpus.write_text(json.dumps(articles), encoding="utf-8")
    stores = []

    monkeypatch.setattr(retriever, "_knowledge_base_path", lambda: corpus)
    monkeypatch.setitem(retriever.CONFIG["rag"], "index_dir", str(tmp_path / "index"))
    monkeypatch.setattr(retriever, "OpenAIEmbeddings", FakeEmbeddings)
    monkeypatch.setattr(
        retriever.FAISS,
        "from_documents",
        lambda documents, embeddings: stores.append(FakeVectorStore(documents)) or stores[-1],
    )
    monkeypatch.setattr(retriever.FAISS, "load_local", lambda directory, embeddings, allow_dangerous_deserialization: stores[0])
    retriever._reset_cache()

    result = retriever.retrieve("a semantic test query")
    second_result = retriever.retrieve("another query")

    assert result[0]["source"] == "KB-TEST"
    assert result[0]["title"] == "Test article"
    assert result[0]["score"] == 0.0
    assert second_result[0]["source"] == "KB-TEST"
    assert len(stores) == 1


def test_retrieve_skips_blank_queries_and_nonpositive_limits(monkeypatch):
    def fail_if_called():
        raise AssertionError("blank queries should not build an embedding index")

    monkeypatch.setattr(retriever, "_get_vector_store", fail_if_called)

    assert retriever.retrieve("   ") == []
    assert retriever.retrieve("query", limit=0) == []
    assert retriever.retrieve("query", limit=-1) == []


def test_retrieve_filters_low_relevance_faiss_distances(monkeypatch):
    relevant = retriever.Document(
        page_content="Relevant",
        metadata={"id": "KB-001", "title": "Relevant", "keywords": [], "content": ""},
    )
    unrelated = retriever.Document(
        page_content="Unrelated",
        metadata={"id": "KB-002", "title": "Unrelated", "keywords": [], "content": ""},
    )

    class RankedStore:
        def similarity_search_with_score(self, query, k):
            return [(relevant, 0.5), (unrelated, 1.5)]

    monkeypatch.setattr(retriever, "_get_vector_store", lambda: RankedStore())
    monkeypatch.setenv("RAG_SCORE_THRESHOLD", "1.0")

    results = retriever.retrieve("semantic query", limit=2)

    assert [result["source"] for result in results] == ["KB-001"]