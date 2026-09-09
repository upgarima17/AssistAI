#!/usr/bin/env sh
set -eu

api_pid=""
if [ -z "${ASSISTAI_API_URL:-}" ] && [ -z "${BACKEND_API_URL:-}" ]; then
    uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000 &
    api_pid=$!
fi

cleanup() {
    if [ -n "$api_pid" ]; then
        kill "$api_pid" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

exec streamlit run streamlit/streamlit_app.py --server.address 0.0.0.0 --server.port "$PORT" --server.headless true --server.enableCORS false --server.enableXsrfProtection false
