# AssistAI IT Support

A local, intentionally small agentic AI assistant for fictional IT support. It demonstrates tool calling, LangGraph state, conditional routing, multi-step workflow, validation, duplicate prevention, and a Streamlit chat interface.

## Architecture

```text
User message + session state
          |
      decide_intent
          |
    conditional route
   /        |         \
knowledge  lookup    creation
   \        |         /
       generate_response
              |
           final answer
```

- `graph.py`: typed `SupportState`, decision node, conditional edges, tool nodes, and response node.
- `tools.py`: three LangChain tools backed by local JSON files.
- `app.py`: Streamlit chat history, employee context, reset control, and visible route/tool status.
- `data/`: sample employee, knowledge-base, and ticket records.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

No API key is required. The intent router and response generation are deterministic so the project works offline. To add an LLM later, replace `decide_intent` and `generate_response` with a structured-output model while keeping the same state and tool boundaries.

Try:

- `How do I reset my VPN password?`
- Set employee ID to `EMP1024`, then ask `What is the status of my laptop issue?`
- Set employee ID to `EMP1024`, then ask `Please raise a ticket: my monitor is flickering and unusable`

Ticket creation writes to `data/tickets.json`. The tool blocks an open duplicate with the same employee and title.
