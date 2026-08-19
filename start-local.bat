@echo off
setlocal
cd /d "%~dp0"
title Neo4j QA RSC (local test)

set "PY_EXE=C:\Program Files\Python311\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=py"

echo Installing deps...
"%PY_EXE%" -m pip install -r requirements.txt -q

echo.
echo Starting Streamlit (RSC edition) at http://127.0.0.1:8501
echo Neo4j: bolt://10.109.17.64:7687
echo.

"%PY_EXE%" -m streamlit run app.py --server.headless true --browser.gatherUsageStats false

echo.
pause
