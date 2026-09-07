#!/usr/bin/env sh
set -eu

uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000 &
api_pid=$!

cleanup() {
    kill "$api_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python - <<'PY'
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

exec streamlit run streamlit/streamlit_app.py --server.address 0.0.0.0 --server.port "$PORT" --server.headless true --server.enableCORS false --server.enableXsrfProtection false
