# AssistIQ IT Support

AssistIQ is a local agentic IT support assistant for a fictional organization. The current stage demonstrates LangGraph orchestration, deterministic tool execution, local RAG, SQLite persistence, validation, duplicate prevention, and a separate FastAPI backend with a Streamlit frontend.

## Current capabilities

- Routes requests to knowledge search, ticket lookup, ticket creation, or clarification.
- Searches `data/knowledge_base.json` with lightweight local lexical retrieval.
- Verifies employees and reads or writes tickets in SQLite.
- Preserves conversation messages and workflow state with a `thread_id`.
- Validates ticket details and blocks similar open duplicate tickets.
- Runs without an API key using deterministic offline responses.
- Optionally uses `OPENAI_API_KEY` and `OPENAI_MODEL` for intent extraction and response wording.

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

The complete architecture diagram is avaialble at(docs/adr/ADR.md)

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

Start the backend in one terminal:

```powershell
uvicorn api:app --app-dir src --reload
```

Start the Streamlit frontend in another terminal:

```powershell
streamlit run streamlit/streamlit_app.py
```

The frontend is normally available at `http://localhost:8501`. The API is available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

Example API request:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{"message":"What is the status of my laptop issue?","employee_id":"EMP1024"}'
```

Pass the returned `thread_id` in later requests to preserve conversation state. Tickets, messages, and workflow state are stored in `data/AssistIQ.sqlite3`. The database can be inspected with a VS Code SQLite extension or another SQLite browser.

## Try it

- `How do I reset my VPN password?`
- Set employee ID to `EMP1024`, then ask `What is the status of my laptop issue?`
- Set employee ID to `EMP1024`, then ask `Please raise a ticket: my monitor is flickering and unusable`

## Documentation

- [Implementation summary](docs/IMPLEMENTATION_SUMMARY.md)
- [LangGraph workflow and diagram](docs/LANGGRAPH_WORKFLOW.md)
- [ADR-0001: Modular support architecture and local persistence](docs/adr/ADR.md)

## Current limitations

This is production-shaped local code, not a deployed enterprise service. Embedding-based retrieval, authentication, authorization, database migrations, structured observability, broader integration coverage, retention policies, and multi-instance database support remain future hardening work.
