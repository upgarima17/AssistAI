# ADR-0001: AssistIQ Modular Support Architecture and Local Persistence

- **Status:** Accepted
- **Date:** 2026-09-03

## Context

AssistIQ is an intelligent employee support assistant with three core capabilities:

- Search IT knowledge
- Look up existing tickets
- Create tickets after validation

The project is no longer limited to a local-only prototype. It now includes a Windows one-click startup flow, a Linux-style startup shell script, and a live Render deployment for demonstration and testing. The frontend and backend remain easy to evolve independently, while conversation state must remain available during and across chat sessions without depending on a fragile in-memory process.

For local development, JSON remains useful for small static reference data. SQLite is still the default persistence layer for tickets and chat state, and the architecture now also supports an optional PostgreSQL connection through `DATABASE_URL` for hosted deployment.

## Decision

Use the following boundaries:

- **LangGraph** owns workflow state, routing, tool execution, and response generation.
- **FastAPI with Uvicorn** exposes the backend over HTTP.
- **Streamlit** is the user interface and will communicate with the backend through that API.
- **RAG** is used for questions about unstructured IT guidance.
- **JSON** stores small reference datasets such as employees and source knowledge articles.
- **SQLite** stores tickets and conversation state.

RAG is not used for ticket status, employee identity, authorization, or ticket creation. Those operations require structured lookups and validation.

### Embedding retrieval

The knowledge-search boundary uses `OpenAIEmbeddings` with a local FAISS vector index. The index is built lazily and persisted under `.assistai_faiss/`; a corpus and embedding-model fingerprint causes it to be rebuilt when either input changes. This provides semantic matching while keeping graph consumers independent of the vector-store implementation. The first index build requires `OPENAI_API_KEY` and network access. FAISS distance scores are returned as opaque numeric ranking metadata and are not compared with the previous lexical scores.

### Deployment model

The project now supports two operating modes:

- Local development: use `start_windows.bat` on Windows or `start_render.sh` in a shell-based environment. The app runs with the default SQLite database and local configuration.
- Hosted deployment: use the Render web service with `PORT=8501` and `start_render.sh` as the start command. If `DATABASE_URL` is configured, the app connects to PostgreSQL; otherwise it falls back to SQLite.

The current public deployment is available at https://assistiq-7s93.onrender.com/.

## Structure

```text
AssistAI/
├── data/
│   ├── employees_example.json
│   ├── knowledge_base.json
│   ├── tickets_example.json
│   └── AssistIQ.sqlite3
├── src/
│   ├── api.py
│   ├── config/
│   ├── graph/
│   │   ├── graph.py
│   │   ├── graph_utils.py
│   │   └── state.py
│   ├── tools/
│   │   └── tools.py
│   ├── rag/
│   ├── storage/
│   └── utils/
├── streamlit/
│   ├── client.py
│   └── streamlit_app.py
├── tests/
│   └── test_graph.py
├── docs/
│   ├── adr/
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── LANGGRAPH_WORKFLOW.md
├── .env.example
├── start_windows.bat
├── start_render.sh
├── pyproject.toml
├── requirements.txt
├── README.md
└── .venv/ (local development only)
```

Backend modules remain under `src`; there is no separate `backend/` folder. Static employee and ticket examples seed the local SQLite database when needed, and the startup scripts standardize local development and deployment configuration.

## Conversation Memory

Each conversation has a stable `thread_id`. The client sends it with each request, and the graph uses it to load and save the conversation in SQLite.

Persist:

- Conversation messages
- Validated employee ID
- Ticket fields collected across turns
- The latest workflow result needed to continue the active conversation

The API, rather than LangGraph's checkpointer, loads and saves this state through the SQLite conversation repository. Do not treat the entire conversation as permanent user memory. Keep only the messages and workflow state needed for the active conversation. Any longer-term user facts require an explicit retention policy.

## Safety and Validation

Before creating a ticket, the workflow must:

1. Validate the employee ID.
2. Collect a meaningful title and description.
3. Search for similar open tickets.
4. Block creation when a similar open ticket already exists.
5. Write the ticket transactionally to SQLite.
6. Return the ticket ID and status from the created record.

When a user explicitly asks for a new or another ticket, the graph clears stale ticket-draft fields from the previous request before collecting new details. A vague fresh-ticket request therefore asks for a new problem description instead of reusing the previous issue. Vague follow-ups such as "still not working, create a ticket" may reuse the prior ticket context.

The assistant must not invent employee details, ticket information, tool results, or knowledge-base content. A RAG response must use retrieved documents and say when no useful document was found.

## Consequences

### Benefits

- The frontend and backend can evolve independently.
- SQLite keeps ticket writes and chat state on disk without requiring another server.
- PostgreSQL can be enabled through `DATABASE_URL` for hosted deployments without changing the higher-level code paths.
- JSON stays simple for reference data.
- RAG handles different ways of asking the same knowledge-base question.
- Storage can later be replaced behind the same service interfaces.
- Local startup automation reduces onboarding friction for Windows and shell-based environments.

### Costs

- SQLite repositories and schema changes add implementation work.
- RAG needs document ingestion, embeddings, and retrieval tests.
- Saved conversations require retention and privacy rules.
- SQLite is suitable for this local and small-scale deployment model, but it is still not the default multi-instance production choice.
- Hosted deployment requires environment configuration and operational awareness for secrets, ports, and external services.

## Migration Plan

The first five steps are now implemented in the local codebase and deployment flow:

1. Keep the deterministic graph as the working baseline.
2. Store ticket reads and writes in SQLite by default.
3. Persist API conversation messages and workflow state keyed by `thread_id`.
4. Put RAG behind the existing knowledge-search tool boundary.
5. Have Streamlit call FastAPI instead of importing graph internals.
6. Add a standard local startup flow with `start_windows.bat` and `start_render.sh` for consistent onboarding.
7. Support hosted deployment through Render with `PORT=8501` and optional PostgreSQL via `DATABASE_URL`.

Remaining hardening:

8. Add authentication, logging, migrations, and broader integration tests before exposing the service widely or at enterprise scale.



## Summary

For this project, use local lexical RAG for knowledge questions, JSON for static reference data, SQLite for tickets and chat state, LangGraph for orchestration, FastAPI for the backend API, and Streamlit as the separate frontend. Ticket creation is validated and duplicate-protected, and each explicit fresh-ticket request starts with a clean ticket draft while preserving the employee and conversation identity.

The current implementation also includes Windows and shell-based startup automation and supports a hosted Render deployment at https://assistiq-7s93.onrender.com/. The architecture remains intentionally simple and local-first, while allowing an optional PostgreSQL-backed environment when `DATABASE_URL` is supplied.
