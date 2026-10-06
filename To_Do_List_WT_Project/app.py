import os
import csv
import io
import sqlite3
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, Response

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "todo.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "todo-list-wt-project")

CATEGORIES = ["Study", "Personal", "Work", "Health", "Shopping", "Other"]
PRIORITIES = ["High", "Medium", "Low"]
STATUSES = ["Pending", "In Progress", "Completed"]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL DEFAULT 'Other',
            priority TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Pending',
            due_date TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )
    """)
    conn.commit()
    count = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
    if count == 0:
        today = date.today()
        demo = [
            ("Complete DAA assignment", "Finish algorithm analysis questions.", "Study", "High", "In Progress", (today + timedelta(days=1)).isoformat()),
            ("Revise CN practical", "Review packet tracer steps before lab.", "Study", "Medium", "Pending", today.isoformat()),
            ("30 min workout", "Shoulder + biceps session.", "Health", "Medium", "Completed", today.isoformat()),
            ("Buy notebook", "Pick up a new practical notebook.", "Shopping", "Low", "Pending", (today + timedelta(days=3)).isoformat()),
        ]
        conn.executemany("""
            INSERT INTO tasks(title,description,category,priority,status,due_date)
            VALUES(?,?,?,?,?,?)
        """, demo)
        conn.commit()
    conn.close()

def task_stats():
    conn = db()
    row = conn.execute("""
        SELECT
          COUNT(*) total,
          SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) completed,
          SUM(CASE WHEN status='In Progress' THEN 1 ELSE 0 END) in_progress,
          SUM(CASE WHEN status='Pending' THEN 1 ELSE 0 END) pending,
          SUM(CASE WHEN status!='Completed' AND due_date IS NOT NULL AND due_date < ? THEN 1 ELSE 0 END) overdue
        FROM tasks
    """, (date.today().isoformat(),)).fetchone()
    conn.close()
    return dict(row)

@app.route("/")
def index():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    priority = (request.args.get("priority") or "").strip()
    category = (request.args.get("category") or "").strip()
    view = (request.args.get("view") or "all").strip()

    sql = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if q:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if status in STATUSES:
        sql += " AND status=?"
        params.append(status)
    if priority in PRIORITIES:
        sql += " AND priority=?"
        params.append(priority)
    if category in CATEGORIES:
        sql += " AND category=?"
        params.append(category)

    today = date.today().isoformat()
    if view == "today":
        sql += " AND due_date=?"
        params.append(today)
    elif view == "overdue":
        sql += " AND status!='Completed' AND due_date IS NOT NULL AND due_date<?"
        params.append(today)
    elif view == "completed":
        sql += " AND status='Completed'"

    sql += """
      ORDER BY
        CASE status WHEN 'In Progress' THEN 1 WHEN 'Pending' THEN 2 ELSE 3 END,
        CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
        CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
        due_date ASC,
        id DESC
    """

    conn = db()
    tasks = conn.execute(sql, params).fetchall()
    recent = conn.execute("""
        SELECT * FROM tasks
        WHERE status='Completed'
        ORDER BY COALESCE(completed_at,created_at) DESC
        LIMIT 5
    """).fetchall()

    cat_rows = conn.execute("""
        SELECT category, COUNT(*) AS total
        FROM tasks GROUP BY category ORDER BY total DESC
    """).fetchall()

    priority_rows = conn.execute("""
        SELECT priority, COUNT(*) AS total
        FROM tasks WHERE status!='Completed'
        GROUP BY priority
    """).fetchall()
    conn.close()

    stats = task_stats()
    total = stats["total"] or 0
    completed = stats["completed"] or 0
    completion_rate = round((completed / total * 100), 1) if total else 0

    return render_template(
        "index.html",
        tasks=tasks,
        recent=recent,
        stats=stats,
        completion_rate=completion_rate,
        categories=CATEGORIES,
        priorities=PRIORITIES,
        statuses=STATUSES,
        today=today,
        q=q,
        status=status,
        priority=priority,
        category=category,
        view=view,
        cat_rows=cat_rows,
        priority_rows=priority_rows,
    )

@app.post("/tasks")
def add_task():
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    category = request.form.get("category") or "Other"
    priority = request.form.get("priority") or "Medium"
    status = request.form.get("status") or "Pending"
    due_date = request.form.get("due_date") or None

    if not title:
        flash("Task title is required.", "danger")
        return redirect(url_for("index"))

    if category not in CATEGORIES:
        category = "Other"
    if priority not in PRIORITIES:
        priority = "Medium"
    if status not in STATUSES:
        status = "Pending"

    completed_at = datetime.now().isoformat(timespec="seconds") if status == "Completed" else None

    conn = db()
    conn.execute("""
        INSERT INTO tasks(title,description,category,priority,status,due_date,completed_at)
        VALUES(?,?,?,?,?,?,?)
    """, (title, description, category, priority, status, due_date, completed_at))
    conn.commit()
    conn.close()
    flash("Task added successfully.", "success")
    return redirect(url_for("index"))

@app.post("/tasks/<int:task_id>/update")
def update_task(task_id):
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    category = request.form.get("category") or "Other"
    priority = request.form.get("priority") or "Medium"
    status = request.form.get("status") or "Pending"
    due_date = request.form.get("due_date") or None

    if not title:
        flash("Task title is required.", "danger")
        return redirect(url_for("index"))

    completed_at = datetime.now().isoformat(timespec="seconds") if status == "Completed" else None

    conn = db()
    conn.execute("""
        UPDATE tasks SET title=?,description=?,category=?,priority=?,status=?,due_date=?,completed_at=?
        WHERE id=?
    """, (title, description, category, priority, status, due_date, completed_at, task_id))
    conn.commit()
    conn.close()
    flash("Task updated.", "success")
    return redirect(url_for("index"))

@app.post("/tasks/<int:task_id>/toggle")
def toggle_task(task_id):
    conn = db()
    task = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
    if task:
        if task["status"] == "Completed":
            conn.execute("UPDATE tasks SET status='Pending',completed_at=NULL WHERE id=?", (task_id,))
        else:
            conn.execute("UPDATE tasks SET status='Completed',completed_at=? WHERE id=?",
                         (datetime.now().isoformat(timespec="seconds"), task_id))
        conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("index"))

@app.post("/tasks/<int:task_id>/delete")
def delete_task(task_id):
    conn = db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    flash("Task deleted.", "success")
    return redirect(request.referrer or url_for("index"))

@app.route("/export.csv")
def export_csv():
    conn = db()
    rows = conn.execute("""
        SELECT title,description,category,priority,status,due_date,created_at,completed_at
        FROM tasks ORDER BY id DESC
    """).fetchall()
    conn.close()

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Title","Description","Category","Priority","Status","Due Date","Created At","Completed At"])
    for r in rows:
        writer.writerow(list(r))

    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=todo_tasks.csv"}
    )

@app.route("/health")
def health():
    return {"status":"ok"}

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
