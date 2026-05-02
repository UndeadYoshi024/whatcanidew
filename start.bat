@echo off
cd /d c:\Dev\dew
set PYTHONPATH=c:\Dev\dew;c:\Dev\dew\pypi
set DEW_LOG_PATH=c:\Dev\dew\logs\routing_decisions.log
start "" "http://localhost:8000"
python -m uvicorn docker.server:app --host 0.0.0.0 --port 8000
