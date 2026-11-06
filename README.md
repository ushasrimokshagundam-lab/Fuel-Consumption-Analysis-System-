# Fuel Consumption Analysis System - deploy-ready

    wsgi.py          production entry point (gunicorn wsgi:app)
    requirements.txt Python packages (root, used by hosts)
    Procfile         Render / Railway / Heroku start command
    render.yaml      Render blueprint
    runtime.txt      Python version (Heroku-style hosts)
    backend/         Flask API + pandas analysis
    frontend/        dashboard (served by Flask)

## Run locally (Windows PowerShell)
    python -m venv venv
    venv\Scripts\python.exe -m pip install -r requirements.txt
    venv\Scripts\python.exe backend\app.py        # http://127.0.0.1:5000
    (set FLASK_DEBUG=1 first for debug mode)

## Deploy on Render (free)
1. Push this folder to a GitHub repo (the files must be at the repo root, next to wsgi.py).
2. Render -> New -> Web Service -> pick the repo.
3. Build command:  pip install -r requirements.txt
   Start command:  gunicorn wsgi:app --workers 1 --threads 4 --timeout 120
4. Deploy. Check https://YOUR-APP.onrender.com/health

## Database on a host
SQLite works for demos but its file is wiped on every redeploy/restart on most free hosts.
For permanent data add a Postgres (or MySQL) database and set the env var DATABASE_URL to its URL.
postgres:// and mysql:// prefixes are converted automatically; tables and sample data are created on first start.

## Notes
- Vercel/Netlify are serverless and not suited to this app. Use Render, Railway, Fly.io or PythonAnywhere.
- On PythonAnywhere: WSGI file should contain  from wsgi import app as application
