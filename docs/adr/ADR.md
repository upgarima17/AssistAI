# ADR-0001: AssistIQ Modular Support Architecture and Local Persistence

- **Status:** Accepted
- **Date:** 2026-09-03

## Context

AssistIQ is an intelligent employee support assistant with three initial capabilities:

- Search IT knowledge
- Look up existing tickets
- Create tickets after validation

The project should demonstrate agent routing and tool use without becoming difficult to run locally. The frontend and backend should be easy to change independently. Conversation state must remain available during a chat and should not disappear every time the API process restarts.

We do not need a hosted database for the current scope. JSON is already useful for small, mostly static data, but it is a poor fit for tickets and conversation state because updates need to be reliable.

## Decision

Use the following boundaries:

- **LangGraph** owns workflow state, routing, tool execution, and response generation.
- **FastAPI with Uvicorn** exposes the backend over HTTP.
- **Streamlit** is the user interface and will communicate with the backend through that API.
- **RAG** is used for questions about unstructured IT guidance.
- **JSON** stores small reference datasets such as employees and source knowledge articles.
- **SQLite** stores tickets and conversation state.

RAG is not used for ticket status, employee identity, authorization, or ticket creation. Those operations require structured lookups and validation.

## Structure

```text
AssistIQ/
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
├── docs/adr/
├── pyproject.toml
└── requirements.txt
```

Backend modules remain under `src`; there is no separate `backend/` folder. Static employee and ticket examples seed the local SQLite database when needed.

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
- JSON stays simple for reference data.
- RAG handles different ways of asking the same knowledge-base question.
- Storage can later be replaced behind the same service interfaces.

### Costs

- SQLite repositories and schema changes add implementation work.
- RAG needs document ingestion, embeddings, and retrieval tests.
- Saved conversations require retention and privacy rules.
- SQLite is intended for this local deployment, not a multi-instance production service.

## Migration Plan

The first five steps are now implemented in the local codebase:

1. Keep the deterministic graph as the working baseline.
2. Store ticket reads and writes in SQLite.
3. Persist API conversation messages and workflow state keyed by `thread_id`.
4. Put RAG behind the existing knowledge-search tool boundary.
5. Have Streamlit call FastAPI instead of importing graph internals.

Remaining hardening:

6. Add authentication, logging, migrations, and integration tests before exposing the service outside the local machine.



## Summary

For this project, use local lexical RAG for knowledge questions, JSON for static reference data, SQLite for tickets and chat state, LangGraph for orchestration, FastAPI for the backend API, and Streamlit as the separate frontend. Ticket creation is validated and duplicate-protected, and each explicit fresh-ticket request starts with a clean ticket draft while preserving the employee and conversation identity.
