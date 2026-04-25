@echo off
echo ========================================
echo  CDIO 3 - 9router + AI Video Assistant
echo ========================================
echo.
echo Starting all services...
echo.

:: Start 9router in first window
echo [1/3] Starting 9router...
start "9router Dashboard" cmd /k "cd /d C:\Users\leduc\OneDrive\Desktop\9router\9router && echo Running 9router... && npm run dev"

:: Wait a moment for 9router to start
timeout /t 3 /nobreak > nul

:: Start Backend API in second window
echo [2/3] Starting Backend API...
start "CDIO 3 Backend" cmd /k "cd /d C:\Users\leduc\OneDrive\Desktop\CDIO 3 && echo Running Backend API... && python -m uvicorn apps.api.main:app --reload --port 8000"

:: Wait a moment for backend to start
timeout /t 2 /nobreak > nul

:: Start Frontend UI in third window
echo [3/3] Starting Frontend UI...
start "CDIO 3 Frontend" cmd /k "cd /d C:\Users\leduc\OneDrive\Desktop\CDIO 3\apps\web-ui && echo Running Frontend UI... && npm run dev"

echo.
echo ========================================
echo All services started successfully!
echo ========================================
echo.
echo Services:
echo   - 9router Dashboard: http://localhost:20128
echo   - Backend API: http://localhost:8000
echo   - Frontend UI: http://localhost:5173
echo.
echo Press any key to exit this window...
pause > nul
