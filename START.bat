@echo off
title AURA TRADES - AI Trading System
color 0A
echo.
echo  ============================================
echo    AURA TRADES V2 - 10-Engine AI Trading
echo   15M ^| 1:2 R:R ^| TradingView MCP Powered
echo  ============================================
echo.
echo  Clearing stale processes on ports 8000/3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr "LISTENING" ^| findstr ":8000"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr "LISTENING" ^| findstr ":3000"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

echo  Starting backend server...
start /B cmd /c "cd /d "%~dp0backend" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 600"
timeout /t 4 /nobreak >nul

echo  Starting frontend server...
start /B cmd /c "cd /d "%~dp0frontend" && npm run dev"
timeout /t 5 /nobreak >nul

echo.
echo  ============================================
echo   AURA TRADES is now running!
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo  ============================================
echo.
echo  Opening browser...
start http://localhost:3000
echo.
echo  Press any key to STOP all servers...
pause >nul

echo.
echo  Shutting down servers...
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *main.py*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000"') do taskkill /F /PID %%a >nul 2>&1
echo  Done. Goodbye!
timeout /t 2 /nobreak >nul
