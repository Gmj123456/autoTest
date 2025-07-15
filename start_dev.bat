@echo off
set FLASK_APP=run.py
set FLASK_ENV=development

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Initialize and upgrade database
python -m flask create_db
python -m flask db upgrade
start "Web Server" python -m flask run --host=0.0.0.0 --port=5000
start "Celery Worker" celery -A app.celery worker --loglevel=info
start "Celery Beat" celery -A app.celery beat --loglevel=info
pause