# Budget Tracker — WT Project

A modern personal finance web application built for a Web Technology project.

## Features
- Secure register/login with password hashing
- Dark responsive dashboard inspired by modern live dashboards
- Income and expense CRUD
- Search + filter transactions
- Monthly category budgets with progress alerts
- Savings goals and progress tracking
- Financial health score
- Category and monthly analytics charts
- CSV export
- SQLite database
- Render-ready deployment

## Project Author
- TUSHAR NAYAK — IU2441230774

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000`.

Create an account. The app automatically adds a small starter dataset so the dashboard looks complete immediately. Delete or edit it from **Transactions**.

## Render deployment
1. Upload this folder to GitHub.
2. In Render choose **New > Web Service** and connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add a random `SECRET_KEY` environment variable if not using `render.yaml`.

> Note: Render's local filesystem may be ephemeral. For a classroom demo SQLite is fine. For production, switch to PostgreSQL or attach a persistent disk and set `DATABASE_PATH`.

## Main files
- `app.py` — Flask routes, authentication, database and business logic
- `templates/` — HTML pages
- `static/css/style.css` — visual design
- `static/js/app.js` — interactions + charts
- `budget_tracker.db` — created automatically on first run
