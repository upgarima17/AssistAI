@echo off
setlocal
cd /d "%~dp0"

REM Use a project-local virtual environment if it exists; otherwise create one.
if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

REM Install dependencies if needed.
python -m pip install -r requirements.txt

REM Launch both services on the default local ports.
set "PORT=8501"
start "AssistAI API" cmd /k "cd /d ""%~dp0"" && call .venv\Scripts\activate.bat && uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000"
start "AssistAI Streamlit" cmd /k "cd /d ""%~dp0"" && call .venv\Scripts\activate.bat && streamlit run streamlit/streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --server.enableCORS false --server.enableXsrfProtection false"

echo.
echo AssistAI is starting...
echo API: http://127.0.0.1:8000
 echo Streamlit: http://localhost:8501
 echo If the app needs OpenAI access, make sure OPENAI_API_KEY is set before running.
echo.
pause
