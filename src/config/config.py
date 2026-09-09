"""Application paths and runtime configuration."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

CONFIG = {
    "llm": {
    "openai_model": "gpt-4o-mini",
    "temperature": 0.3
    },

    "rag": {
    "embedding_model": "text-embedding-3-small",
    "index_dir": str(PROJECT_ROOT / ".assistai_faiss"),
    "top_k": 3,
    "score_threshold": 1.2
    },
    
    "evaluation": {
    "criteria": [
    "tone_empathy",
    "knowledge_accuracy",
    "resolution_quality"
    ],
    "score_range": [1, 5]
    },
    

    }
    