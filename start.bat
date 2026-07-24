@echo off
REM MarketMind — Server Startup
REM Run this every time you want to start the AI backend.
REM Make sure Ollama is already running before you run this.

echo ================================================
echo  MarketMind AI Server
echo  http://localhost:8000
echo  Mobile app: http://[your-ip]:8000
echo ================================================
echo.

REM Set OLLAMA_KEEP_ALIVE so model stays pinned in RAM
set OLLAMA_KEEP_ALIVE=-1

REM Copy .env.example to .env on first run if needed
if not exist .env (
    copy .env.example .env
    echo [INFO] Created .env from .env.example
)

REM Run the server
python server.py

pause
