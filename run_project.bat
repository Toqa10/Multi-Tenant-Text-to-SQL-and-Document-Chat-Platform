@echo off
title Multi-Tenant Text-to-SQL AI Platform
echo ============================================================
echo  Multi-Tenant Text-to-SQL and Document Chat Platform
echo ============================================================
echo.

echo [1/3] Starting Backend API Server (port 8000)...
start "Backend API" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 4 /nobreak > nul

echo [2/3] Starting Celery Flower Dashboard (port 5555)...
start "Celery Flower" cmd /k "cd /d %~dp0backend && python -m celery -A app.workers.celery_app flower --port=5555 --broker=redis://localhost:6379/1"
timeout /t 2 /nobreak > nul

echo [3/3] Starting Frontend UI (port 5173)...
start "Frontend UI" cmd /k "cd /d %~dp0frontend && npm run dev -- --host"
timeout /t 3 /nobreak > nul

echo.
echo ============================================================
echo  All services are starting up!
echo ============================================================
echo.
echo  [Frontend UI]          http://localhost:5173
echo  [Backend API]          http://localhost:8000
echo  [API Docs Swagger]     http://localhost:8000/docs
echo  [Celery Flower]        http://localhost:5555
echo.
echo  Note: Prometheus, Grafana and MinIO require Docker Desktop.
echo  Install Docker Desktop from https://www.docker.com/products/docker-desktop/
echo  Then run: cd backend && docker compose up -d
echo ============================================================
echo.
pause
