@echo off
echo ===========================================
echo   AQI Insight Dashboard - Run Script
echo ===========================================

echo.
echo [1/3] Starting Backend API...
start "AQI Backend API" cmd /k "uvicorn backend.main:app --reload"

timeout /t 5 /nobreak >nul

echo.
echo [2/3] Starting Frontend Dashboard...
start "AQI Dashboard" cmd /k "streamlit run frontend/app.py"

echo.
echo [3/3] Done! Application should be opening in your browser.
echo ===========================================
echo Use 'backend/scripts/init_db.py', 'ingest_data.py', and 'train_models.py'
echo to re-initialize data if needed.
pause
