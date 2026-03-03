@echo off
echo Starting SIA-RAG Backend...
cd /d "%~dp0"
start "SIA-RAG Backend" cmd /k "uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload"
echo.
echo ✅ Backend running at http://localhost:8000
echo    Docs:     http://localhost:8000/docs
echo    Frontend: open frontend\index.html in your browser
echo.
pause
