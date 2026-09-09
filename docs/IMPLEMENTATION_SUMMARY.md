# AssistIQ Implementation Summary

## Purpose

AssistIQ is an intelligent employee support assistant for a fictional organization. It demonstrates agent routing, tool execution, state management, validation, retrieval, and a separate frontend/backend setup.

## What Was Implemented

### Modular project structure

The backend files are kept directly under `src`, and the Streamlit application remains separate under `streamlit`. The repository also includes startup automation for local development and deployment.

```text
AssistAI/
├── data/
│   ├── employees_example.json
│   ├── knowledge_base.json
│   ├── tickets_example.json
│   └── assistai.sqlite3
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
├── docs/
│   ├── adr/
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── LANGGRAPH_WORKFLOW.md
├── .env.example
├── start_windows.bat
├── start_render.sh
├── tests/
├── pyproject.toml
├── requirements.txt
├── README.md
└── .venv/ (local only)
```

### Agent workflow

`src/graph/graph.py` contains the LangGraph workflow:

See the detailed workflow reference in [LANGGRAPH_WORKFLOW.md](LANGGRAPH_WORKFLOW.md).

1. Read the user's request.
2. Detect the intended action.
3. Route conditionally to knowledge search, ticket lookup, ticket creation, or clarification.
4. Execute the selected tool.
5. Generate a user-friendly response.

The workflow state contains the request, employee ID, intent, ticket details, tool result, response, errors, and retrieved source IDs. Explicit requests for a new or another ticket clear stale ticket-draft fields before collecting new details. Vague follow-ups such as "still not working, create a ticket" can reuse the previous ticket context.

### Tools

The assistant has three tool boundaries in `src/tools/tools.py`:

- `knowledge_search`: retrieves relevant IT guidance through the RAG retrieval layer.
- `ticket_lookup`: searches tickets through the SQLite repository.
- `ticket_create`: creates a ticket in SQLite after validation and duplicate detection.

The tools are implemented as LangChain tools, so they can later be connected to an LLM's function-calling workflow without changing their storage responsibilities.

### RAG knowledge search

The RAG boundary is in `src/rag/retriever.py`. It uses OpenAI embeddings with a local FAISS index built from `data/knowledge_base.json`. The index is created lazily on the first knowledge query, stored in `.assistai_faiss/`, and rebuilt when the corpus or configured embedding model changes. Retrieval returns the original article fields, source ID, and FAISS distance score, excluding results above the configurable `RAG_SCORE_THRESHOLD` distance cutoff.

The first embedding query requires network access and `OPENAI_API_KEY`; subsequent process calls reuse the in-memory index, and subsequent runs can load the persisted index. Knowledge responses include their source IDs, and the assistant reports when no relevant article is found. RAG remains limited to unstructured IT guidance; tickets and employee data use structured storage.

### LLM utility

`src/utils/llm.py` is the single model-loading boundary. It reads `OPENAI_API_KEY` and `OPENAI_MODEL` from `.env`, caches the configured `ChatOpenAI` client, and generates grounded response wording from verified tool results. When no key is configured or the model fails, the graph uses its deterministic response path instead.

### Local persistence and deployment database support

SQLite is used for data that changes during normal operation:

- Tickets
- Conversation state
- Chat messages

`src/storage/database.py` creates the schema and seeds initial data when needed. SQLite uses transactions and WAL mode, making it a safer local choice than rewriting JSON files for every ticket operation.

Employee and knowledge-base reference data remain in JSON because they are small and mostly read-only. The project also supports an optional PostgreSQL deployment mode via `DATABASE_URL`, which is used automatically when configured in a hosted environment such as Render.

### Persistent conversation memory

The FastAPI API assigns a `thread_id` to each conversation. The client sends that ID with later messages. The API loads the previous state from SQLite, runs the graph, and saves the updated messages and workflow state.

This means conversation state survives API restarts. The current implementation stores state locally and in process-independent SQLite, but it does not yet implement authentication or long-term personal memory. Those concerns should be added before handling real employee data.

### FastAPI and Streamlit separation

`src/api.py` exposes:

- `GET /health`
- `POST /chat`

The Streamlit application uses `streamlit/client.py` to call the API. It does not import or execute the graph directly. This gives the frontend and backend independent boundaries and makes it possible to replace Streamlit later.

## How To Run

### Windows: one-click startup

From the project root:

```powershell
start_windows.bat
```

This script creates a virtual environment if needed, installs dependencies, and starts both the FastAPI backend and the Streamlit frontend.

### Windows PowerShell

```powershell
cd path\to\AssistAI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

In a second terminal:

```powershell
streamlit run streamlit/streamlit_app.py
```

### Git Bash / Linux

```bash
cd /path/to/AssistAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PORT=8501
./start_render.sh
```

For Git Bash on Windows:

```bash
cd /c/path/to/AssistAI
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
export PORT=8501
bash ./start_render.sh
```

The Streamlit UI is normally available at `http://localhost:8501`. The API documentation is available at `http://127.0.0.1:8000/docs`.

## Safety Measures

- Employee IDs are checked against `employees_example.json` before ticket operations.
- Ticket creation requires a meaningful description.
- Similar open tickets are detected and blocked before creating a new ticket.
- Explicit fresh-ticket requests do not reuse the previous ticket's details.
- The response does not fabricate ticket IDs or statuses.
- Knowledge responses are based on retrieved local articles.
- API and tool failures are returned as controlled errors.
- Local secrets and generated SQLite files are excluded through `.gitignore`.

## Current Limitations

This is production-shaped local code, and the project now also includes a live hosted deployment. The following work remains for hardening and wider production use:

- Add authentication and authorization.
- Add database migrations instead of startup-only schema creation.
- Add structured logging, metrics, and request IDs.
- Add stronger API and integration test coverage.
- Add retention and deletion policies for conversation data.
- Use a shared database for multi-instance deployment beyond the current local and Render-based demo setup.

The project is currently available at https://assistiq-7s93.onrender.com/.

## Related Decision

The architectural decisions and rejected alternatives are recorded in [ADR-0001](adr/ADR.md).
