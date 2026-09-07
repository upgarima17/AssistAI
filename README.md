# AssistIQ IT Support

AssistIQ is a local agentic IT support assistant for a fictional organization. The current stage demonstrates LangGraph orchestration, deterministic tool execution, local RAG, SQLite persistence, validation, duplicate prevention, and a separate FastAPI backend with a Streamlit frontend.

## Problem statement

Employees need a single place to get IT troubleshooting guidance, check existing support tickets, and report new issues. The assistant must route each request correctly, use trusted local knowledge, validate employee and ticket data, and avoid creating duplicate tickets.

## Solution overview

AssistIQ combines a LangGraph workflow with local tools. Knowledge questions use embedding-based RAG over the local knowledge base, while employee and ticket operations use validated JSON and SQLite repositories. FastAPI exposes the backend, and Streamlit provides the user interface.

## Current capabilities

- Routes requests to knowledge search, ticket lookup, ticket creation, or clarification.
- Searches `data/knowledge_base.json` with OpenAI embeddings and a local FAISS index.
- Verifies employees and reads or writes tickets in SQLite.
- Preserves conversation messages and workflow state with a `thread_id`.
- Validates ticket details and blocks similar open duplicate tickets.
- Uses deterministic graph responses when no chat model is configured; the first embedding-based knowledge query requires `OPENAI_API_KEY`.
- Optionally uses `OPENAI_MODEL` for intent extraction and response wording.

## Technology stack

- **Python**: application language
- **LangGraph**: workflow state, routing, and orchestration
- **LangChain**: tool and model integration
- **OpenAI**: chat responses and text embeddings
- **FAISS**: local vector similarity search
- **FastAPI and Uvicorn**: backend API and server
- **Streamlit**: frontend interface
- **SQLite**: tickets and conversation persistence
- **JSON**: small, mostly static reference data


## Architecture

```text
User message + thread state
                |
            decide
                |
      conditional route
    /       |       |       \
knowledge lookup  create  clarify
    \       |       |       /
          generate_response
                     |
                 final answer
```

The complete architecture decision record is available in [ADR-0001](docs/adr/ADR.md).

## Project layout

```text
AssistAI/
├── data/                       # JSON reference data and SQLite databases
├── src/
│   ├── api.py                  # FastAPI HTTP boundary
│   ├── config/                 # Application configuration
│   ├── graph/                  # LangGraph workflow and typed state
│   ├── rag/                    # Local knowledge retrieval
│   ├── storage/                # SQLite repositories and persistence
│   ├── tools/                  # LangChain tool boundaries
│   └── utils/                  # Configuration and LLM helpers
├── streamlit/                  # Streamlit UI and API client
├── tests/                      # Graph behavior tests
├── docs/
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── LANGGRAPH_WORKFLOW.md   # Workflow explanation and diagram
│   └── adr/ADR.md              # Architecture Decision Record
├── pyproject.toml
└── requirements.txt
```

## Run locally

Create and activate a virtual environment from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment variables

Copy `.env.example` to `.env` and configure the following values:

| Variable | Required | Purpose | Default |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes for embeddings; optional for LLM responses | Authenticates OpenAI embedding and chat requests | None |
| `OPENAI_MODEL` | No | Chat model used for intent and response wording | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | No | Embedding model used by the FAISS index | `text-embedding-3-small` |
| `RAG_SCORE_THRESHOLD` | No | Maximum FAISS distance accepted as a relevant result | `1.2` |
| `DATABASE_URL` | No locally; required for PostgreSQL deployment | PostgreSQL connection URL | SQLite database in `data/` |

The first embedding-based knowledge search requires network access and `OPENAI_API_KEY`. If no chat model is available, the application uses deterministic response logic.

Start the backend in one terminal:

```powershell
uvicorn api:app --app-dir src --reload
```

Start the Streamlit frontend in another terminal:

```powershell
streamlit run streamlit/streamlit_app.py
```

The frontend is normally available at `http://localhost:8501`. The API is available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

### Render deployment

Create a Render PostgreSQL database and add its internal connection URL as `DATABASE_URL` in the web service environment variables. The application automatically uses PostgreSQL when `DATABASE_URL` is set and keeps SQLite for local development when it is absent.

Use these Render commands for the combined FastAPI and Streamlit service:

```text
Build Command: pip install -r requirements.txt
Start Command: sh start_render.sh
```

Also configure `OPENAI_API_KEY` and `ASSISTAI_API_URL=http://127.0.0.1:8000`. PostgreSQL stores tickets and conversations persistently; the local FAISS index can be rebuilt after a service restart.

Example API request:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{"message":"What is the status of my laptop issue?","employee_id":"EMP1024"}'
```

Pass the returned `thread_id` in later requests to preserve conversation state. Tickets, messages, and workflow state are stored in `data/AssistIQ.sqlite3`. The database can be inspected with a VS Code SQLite extension or another SQLite browser.

## Try it

- `How do I reset my VPN password?`
- Set employee ID to `EMP1024`, then ask `What is the status of my laptop issue?`
- Set employee ID to `EMP1024`, then ask `Please raise a ticket: my monitor is flickering and unusable`

## Sample outputs

Knowledge search:

```text
Reset your VPN password (KB-001)

Open the AssistIQ VPN portal, choose Forgot password, verify with your employee ID, and set a new password.
```

Ticket lookup:

```text
Here are the matching tickets:
- TICKET-1001: Laptop will not start - Open (High)
```

Ticket creation:

```text
Ticket TICKET-1003 created successfully. Status: Open; priority: Medium.
```

## Key design decisions

- LangGraph owns routing and workflow state, while tools own their storage operations.
- RAG is used for unstructured IT guidance; structured ticket and employee operations do not use semantic search.
- JSON is used for small reference data, while SQLite handles changing ticket and conversation data transactionally.
- FastAPI and Streamlit communicate through an API boundary so the frontend and backend can evolve independently.
- Ticket creation validates employees, requires meaningful details, and blocks similar open tickets.
- The FAISS index is persisted locally and rebuilt when the knowledge base or embedding model changes.

More detail is available in [ADR-0001](docs/adr/ADR.md).

## Documentation

- [Implementation summary](docs/IMPLEMENTATION_SUMMARY.md)
- [LangGraph workflow and diagram](docs/LANGGRAPH_WORKFLOW.md)
- [ADR-0001: Modular support architecture and local persistence](docs/adr/ADR.md)

## Current limitations

This is production-shaped local code, not a deployed enterprise service. Authentication, authorization, database migrations, structured observability, broader integration coverage, retention policies, and multi-instance database support remain future hardening work. The FAISS index is generated in `.assistai_faiss/` and rebuilt automatically when the knowledge-base JSON changes.
