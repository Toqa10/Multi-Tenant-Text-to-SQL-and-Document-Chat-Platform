@echo off
echo Starting AI Platform Services...

echo Starting Backend API (Port 8000)...
start "AI Backend" cmd /c "cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Starting Frontend UI (Port 5173)...
start "AI Frontend" cmd /c "cd frontend && npm run dev -- --host"

echo Services are starting up!
echo ----------------------------------------------------
echo Frontend UI: http://localhost:5173
echo Backend API: http://localhost:8000/docs
echo ----------------------------------------------------
echo To stop the servers, just close the new command prompt windows that opened.
pause
