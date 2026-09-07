#!/usr/bin/env sh
set -eu

api_log=/tmp/assistai-api.log
uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000 >"$api_log" 2>&1 &
api_pid=$!

cleanup() {
    kill "$api_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if ! python - <<'PY'
import sys
import time
import urllib.request

for _ in range(30):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as response:
            if response.status == 200:
                break
    except Exception:
        time.sleep(1)
else:
    sys.exit("FastAPI did not become ready on port 8000")
PY
then
    echo "FastAPI startup failed. Uvicorn log:" >&2
    cat "$api_log" >&2 || true
    exit 1
fi

exec streamlit run streamlit/streamlit_app.py --server.address 0.0.0.0 --server.port "$PORT" --server.headless true --server.enableCORS false --server.enableXsrfProtection false
