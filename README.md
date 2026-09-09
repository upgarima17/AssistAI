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

### 1) Install dependencies

From the project root, create a virtual environment and install the required packages.

#### Windows PowerShell

```powershell
cd path\to\AssistAI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Git Bash (Windows)

```bash
cd /c/path/to/AssistAI
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

#### Linux / macOS

```bash
cd /path/to/AssistAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Set environment variables

Create a local environment file:

```bash
cp .env.example .env
```

Then update `.env` with the values you need:

| Variable | Required | Purpose | Default |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes for embeddings and LLM calls | Authenticates OpenAI requests | None |
| `OPENAI_MODEL` | No | Chat model used for routing and response wording | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | No | Embedding model used by the FAISS index | `text-embedding-3-small` |
| `RAG_SCORE_THRESHOLD` | No | Maximum FAISS relevance distance | `1.0` |
| `DATABASE_URL` | No locally; required for PostgreSQL deployment | PostgreSQL connection URL | SQLite in `data/` |

The first knowledge lookup requires an OpenAI embedding request, so `OPENAI_API_KEY` should be set before the first RAG search. If no model is configured, the app falls back to deterministic logic.

### 3) Start the app

#### Option A: One-click startup on Windows

Run the included launcher from the project root:

```powershell
start_windows.bat
```

Or double-click `start_windows.bat` in Windows Explorer.

This script creates a local `.venv` if needed, installs dependencies, and starts:

- FastAPI backend: `http://127.0.0.1:8000`
- Streamlit UI: `http://localhost:8501`

#### Option B: Manual startup in two terminals

Start the backend in one terminal:

```bash
uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

Start the frontend in a second terminal:

```bash
streamlit run streamlit/streamlit_app.py
```

#### Option C: Linux / Git Bash launch

From the project root:

```bash
export PORT=8501
./start_render.sh
```

In Git Bash on Windows, use:

```bash
export PORT=8501
bash ./start_render.sh
```

This script starts the API and Streamlit together for a local Linux-like environment.

The frontend is normally available at `http://localhost:8501`. The API is available at `http://127.0.0.1:8000`, with interactive API docs at `http://127.0.0.1:8000/docs`.

## Deployment

The project is live at:

https://assistiq-7s93.onrender.com/

For Render, use the startup script and set the port before launch:

```text
Build Command: pip install -r requirements.txt
Start Command: PORT=8501 sh start_render.sh
```

Also configure the following service environment variables in Render:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `RAG_SCORE_THRESHOLD`
- `DATABASE_URL` (optional, for persistent PostgreSQL storage)

When `DATABASE_URL` is present, the app automatically uses PostgreSQL. Without it, local development continues with the SQLite database in `data/`.

Example API request:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{"message":"What is the status of my laptop issue?","employee_id":"EMP1024"}'
```

Pass the returned `thread_id` in later requests to preserve conversation state. Tickets, messages, and workflow state are stored in `data/AssistIQ.sqlite3`. The database can be inspected with a VS Code SQLite extension or another SQLite browser.

## Try it

- `How do I reset my VPN password?`
- Set employee ID to `EMP1024`, then ask `What is the status of my laptop issue?`
- Set employee ID to `EMP1024`, then ask `Please raise a ticket: my monitor is flickering and unusable`
- Without setting employee ID - Just ask `Tell me about my ticket status` Agent will proceed with asking employee Id , caht with it for Ticket Status,Ticket Creation or any regular issue you are facing like `My Vpn is not working`

## Sample outputs

Knowledge search:

```text
Reset your VPN password (KB-001)

Open the AssistIQ VPN portal, choose Forgot password, verify with your employee ID, and set a new password.
```

Ticket lookup:

```text
I found a ticket for employee ID EMP2048. Here are the details:

Ticket ID: INC-1002
Title: VPN access issue
Description: VPN disconnects during sign-in.
Status: Waiting for user
Priority: Medium
If you need further assistance, feel free to ask!pen (High)
```

Ticket creation:

```text
 ticket has been successfully created for the laptop not starting issue. Here are the details:

Ticket ID: INC-1005
Title: Laptop not starting
Description: Laptop not starting
Status: New
Priority: Medium
Created At: September 9, 2026
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
