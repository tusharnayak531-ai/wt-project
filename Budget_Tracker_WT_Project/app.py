import os
import sqlite3
import csv
import io
from datetime import date, datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'budget_tracker.db'))

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production-budget-tracker')

CATEGORIES = ['Food', 'Travel', 'Shopping', 'Bills', 'Education', 'Entertainment', 'Health', 'Rent', 'Salary', 'Freelance', 'Other']
EXPENSE_CATEGORIES = ['Food', 'Travel', 'Shopping', 'Bills', 'Education', 'Entertainment', 'Health', 'Rent', 'Other']


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('income','expense')),
        amount REAL NOT NULL CHECK(amount > 0),
        category TEXT NOT NULL,
        note TEXT,
        tx_date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        monthly_limit REAL NOT NULL CHECK(monthly_limit > 0),
        month TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, category, month),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        target REAL NOT NULL CHECK(target > 0),
        saved REAL NOT NULL DEFAULT 0 CHECK(saved >= 0),
        deadline TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    ''')
    conn.commit()
    conn.close()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper


def money(v):
    return f"₹{float(v or 0):,.0f}"

app.jinja_env.filters['money'] = money


def current_month():
    return date.today().strftime('%Y-%m')


def month_bounds(month):
    # SQLite substr(tx_date,1,7) is used, so this validates month only.
    try:
        datetime.strptime(month, '%Y-%m')
        return month
    except Exception:
        return current_month()


def get_month_summary(user_id, month):
    conn = db()
    rows = conn.execute('''
        SELECT type, COALESCE(SUM(amount),0) AS total
        FROM transactions
        WHERE user_id=? AND substr(tx_date,1,7)=?
        GROUP BY type
    ''', (user_id, month)).fetchall()
    vals = {'income': 0.0, 'expense': 0.0}
    for r in rows:
        vals[r['type']] = float(r['total'] or 0)
    vals['balance'] = vals['income'] - vals['expense']
    vals['savings_rate'] = round((vals['balance'] / vals['income'] * 100), 1) if vals['income'] > 0 else 0
    conn.close()
    return vals


def category_spend(user_id, month):
    conn = db()
    rows = conn.execute('''
        SELECT category, ROUND(SUM(amount),2) AS total
        FROM transactions
        WHERE user_id=? AND type='expense' AND substr(tx_date,1,7)=?
        GROUP BY category ORDER BY total DESC
    ''', (user_id, month)).fetchall()
    conn.close()
    return rows


def budget_status(user_id, month):
    conn = db()
    rows = conn.execute('''
        SELECT b.id, b.category, b.monthly_limit,
               COALESCE(SUM(t.amount),0) AS spent
        FROM budgets b
        LEFT JOIN transactions t ON t.user_id=b.user_id
          AND t.type='expense' AND t.category=b.category
          AND substr(t.tx_date,1,7)=b.month
        WHERE b.user_id=? AND b.month=?
        GROUP BY b.id, b.category, b.monthly_limit
        ORDER BY b.category
    ''', (user_id, month)).fetchall()
    conn.close()
    out=[]
    for r in rows:
        limit=float(r['monthly_limit'])
        spent=float(r['spent'])
        pct=round(spent/limit*100,1) if limit else 0
        out.append(dict(r) | {'percent': pct, 'remaining': limit-spent})
    return out


def health_score(summary, budgets):
    score=100
    if summary['income'] <= 0:
        score -= 20
    if summary['income'] > 0:
        ratio=summary['expense']/summary['income']
        if ratio > 1: score -= 35
        elif ratio > .9: score -= 22
        elif ratio > .75: score -= 12
    over=sum(1 for b in budgets if b['percent'] > 100)
    near=sum(1 for b in budgets if 80 <= b['percent'] <= 100)
    score -= min(30, over*12 + near*5)
    if summary['savings_rate'] >= 20: score += 5
    return max(0,min(100,int(score)))


@app.route('/')
def index():
    return redirect(url_for('dashboard' if 'user_id' in session else 'login'))


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name=request.form.get('name','').strip()
        email=request.form.get('email','').strip().lower()
        password=request.form.get('password','')
        if not name or not email or len(password) < 6:
            flash('Enter your name, email and a password of at least 6 characters.', 'danger')
            return redirect(url_for('register'))
        conn=db()
        try:
            cur=conn.execute('INSERT INTO users(name,email,password_hash) VALUES(?,?,?)',
                             (name,email,generate_password_hash(password)))
            conn.commit()
            uid=cur.lastrowid
            # Helpful starter data for a polished first-run demo.
            today=date.today().isoformat()
            month=current_month()
            demo=[
                (uid,'income',35000,'Salary','Monthly allowance / income',today),
                (uid,'expense',1850,'Food','Meals and snacks',today),
                (uid,'expense',900,'Travel','Fuel / transport',today),
                (uid,'expense',1200,'Education','Books and course material',today),
            ]
            conn.executemany('INSERT INTO transactions(user_id,type,amount,category,note,tx_date) VALUES(?,?,?,?,?,?)', demo)
            conn.executemany('INSERT OR IGNORE INTO budgets(user_id,category,monthly_limit,month) VALUES(?,?,?,?)', [
                (uid,'Food',6000,month),(uid,'Travel',4000,month),(uid,'Shopping',5000,month),(uid,'Entertainment',3000,month)
            ])
            conn.execute('INSERT INTO goals(user_id,name,target,saved,deadline) VALUES(?,?,?,?,?)',
                         (uid,'Emergency Fund',50000,12500,None))
            conn.commit()
            session['user_id']=uid
            session['user_name']=name
            flash('Account created. Starter demo data has been added.', 'success')
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash('An account with that email already exists.', 'danger')
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email=request.form.get('email','').strip().lower()
        password=request.form.get('password','')
        conn=db(); user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone(); conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id']=user['id']; session['user_name']=user['name']
            return redirect(url_for('dashboard'))
        flash('Incorrect email or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    month=month_bounds(request.args.get('month', current_month()))
    uid=session['user_id']
    summary=get_month_summary(uid,month)
    cats=category_spend(uid,month)
    budgets=budget_status(uid,month)
    conn=db()
    recent=conn.execute('SELECT * FROM transactions WHERE user_id=? ORDER BY tx_date DESC,id DESC LIMIT 7',(uid,)).fetchall()
    goals=conn.execute('SELECT * FROM goals WHERE user_id=? ORDER BY id DESC LIMIT 3',(uid,)).fetchall()
    conn.close()
    alerts=[]
    for b in budgets:
        if b['percent'] > 100: alerts.append(('danger', f"{b['category']} budget exceeded by {money(abs(b['remaining']))}."))
        elif b['percent'] >= 80: alerts.append(('warning', f"{b['category']} budget is {b['percent']:.0f}% used."))
    if summary['income'] > 0 and summary['expense'] > summary['income']:
        alerts.append(('danger','Expenses are higher than income this month.'))
    score=health_score(summary,budgets)
    return render_template('dashboard.html',month=month,summary=summary,cats=cats,budgets=budgets,recent=recent,goals=goals,alerts=alerts,score=score)


@app.route('/transactions', methods=['GET','POST'])
@login_required
def transactions():
    uid=session['user_id']
    if request.method == 'POST':
        tx_type=request.form.get('type')
        amount=request.form.get('amount',type=float)
        category=request.form.get('category','Other')
        tx_date=request.form.get('tx_date') or date.today().isoformat()
        note=request.form.get('note','').strip()
        if tx_type not in ('income','expense') or not amount or amount <= 0:
            flash('Enter a valid transaction.', 'danger')
        else:
            conn=db(); conn.execute('INSERT INTO transactions(user_id,type,amount,category,note,tx_date) VALUES(?,?,?,?,?,?)',
                                   (uid,tx_type,amount,category,note,tx_date)); conn.commit(); conn.close()
            flash('Transaction added.', 'success')
        return redirect(url_for('transactions'))
    q=request.args.get('q','').strip(); typ=request.args.get('type',''); month=request.args.get('month','')
    sql='SELECT * FROM transactions WHERE user_id=?'; params=[uid]
    if q:
        sql+=' AND (category LIKE ? OR note LIKE ?)'; params += [f'%{q}%',f'%{q}%']
    if typ in ('income','expense'):
        sql+=' AND type=?'; params.append(typ)
    if month:
        sql+=' AND substr(tx_date,1,7)=?'; params.append(month)
    sql+=' ORDER BY tx_date DESC,id DESC'
    conn=db(); rows=conn.execute(sql,params).fetchall(); conn.close()
    return render_template('transactions.html',rows=rows,categories=CATEGORIES,today=date.today().isoformat(),q=q,typ=typ,month=month)


@app.post('/transactions/<int:tx_id>/edit')
@login_required
def edit_transaction(tx_id):
    uid=session['user_id']
    tx_type=request.form.get('type'); amount=request.form.get('amount',type=float); category=request.form.get('category','Other'); tx_date=request.form.get('tx_date'); note=request.form.get('note','').strip()
    if tx_type in ('income','expense') and amount and amount>0 and tx_date:
        conn=db(); conn.execute('UPDATE transactions SET type=?,amount=?,category=?,note=?,tx_date=? WHERE id=? AND user_id=?',
                               (tx_type,amount,category,note,tx_date,tx_id,uid)); conn.commit(); conn.close(); flash('Transaction updated.','success')
    return redirect(url_for('transactions'))


@app.post('/transactions/<int:tx_id>/delete')
@login_required
def delete_transaction(tx_id):
    conn=db(); conn.execute('DELETE FROM transactions WHERE id=? AND user_id=?',(tx_id,session['user_id'])); conn.commit(); conn.close()
    flash('Transaction deleted.','success'); return redirect(url_for('transactions'))


@app.route('/budgets', methods=['GET','POST'])
@login_required
def budgets():
    uid=session['user_id']; month=month_bounds(request.values.get('month',current_month()))
    if request.method == 'POST':
        category=request.form.get('category'); limit=request.form.get('monthly_limit',type=float)
        if category in EXPENSE_CATEGORIES and limit and limit>0:
            conn=db(); conn.execute('''INSERT INTO budgets(user_id,category,monthly_limit,month) VALUES(?,?,?,?)
                ON CONFLICT(user_id,category,month) DO UPDATE SET monthly_limit=excluded.monthly_limit''',(uid,category,limit,month)); conn.commit(); conn.close(); flash('Budget saved.','success')
        return redirect(url_for('budgets',month=month))
    return render_template('budgets.html',month=month,budgets=budget_status(uid,month),categories=EXPENSE_CATEGORIES)


@app.post('/budgets/<int:budget_id>/delete')
@login_required
def delete_budget(budget_id):
    conn=db(); conn.execute('DELETE FROM budgets WHERE id=? AND user_id=?',(budget_id,session['user_id'])); conn.commit(); conn.close(); flash('Budget removed.','success'); return redirect(request.referrer or url_for('budgets'))


@app.route('/goals', methods=['GET','POST'])
@login_required
def goals():
    uid=session['user_id']
    if request.method=='POST':
        name=request.form.get('name','').strip(); target=request.form.get('target',type=float); saved=request.form.get('saved',type=float) or 0; deadline=request.form.get('deadline') or None
        if name and target and target>0 and saved>=0:
            conn=db(); conn.execute('INSERT INTO goals(user_id,name,target,saved,deadline) VALUES(?,?,?,?,?)',(uid,name,target,saved,deadline)); conn.commit(); conn.close(); flash('Savings goal created.','success')
        return redirect(url_for('goals'))
    conn=db(); rows=conn.execute('SELECT * FROM goals WHERE user_id=? ORDER BY id DESC',(uid,)).fetchall(); conn.close()
    return render_template('goals.html',rows=rows)


@app.post('/goals/<int:goal_id>/update')
@login_required
def update_goal(goal_id):
    saved=request.form.get('saved',type=float)
    if saved is not None and saved>=0:
        conn=db(); conn.execute('UPDATE goals SET saved=? WHERE id=? AND user_id=?',(saved,goal_id,session['user_id'])); conn.commit(); conn.close(); flash('Goal progress updated.','success')
    return redirect(url_for('goals'))


@app.post('/goals/<int:goal_id>/delete')
@login_required
def delete_goal(goal_id):
    conn=db(); conn.execute('DELETE FROM goals WHERE id=? AND user_id=?',(goal_id,session['user_id'])); conn.commit(); conn.close(); flash('Goal deleted.','success'); return redirect(url_for('goals'))


@app.route('/analytics')
@login_required
def analytics():
    uid=session['user_id']; month=month_bounds(request.args.get('month',current_month()))
    conn=db()
    monthly=conn.execute('''
      SELECT substr(tx_date,1,7) m,
      ROUND(SUM(CASE WHEN type='income' THEN amount ELSE 0 END),2) income,
      ROUND(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),2) expense
      FROM transactions WHERE user_id=? GROUP BY m ORDER BY m DESC LIMIT 6
    ''',(uid,)).fetchall()
    conn.close()
    monthly=list(reversed(monthly))
    return render_template('analytics.html',month=month,cats=category_spend(uid,month),monthly=monthly,summary=get_month_summary(uid,month))


@app.route('/export.csv')
@login_required
def export_csv():
    conn=db(); rows=conn.execute('SELECT type,amount,category,note,tx_date FROM transactions WHERE user_id=? ORDER BY tx_date DESC',(session['user_id'],)).fetchall(); conn.close()
    out=io.StringIO(); w=csv.writer(out); w.writerow(['Type','Amount','Category','Note','Date'])
    for r in rows: w.writerow([r['type'],r['amount'],r['category'],r['note'],r['tx_date']])
    return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=budget_transactions.csv'})


@app.route('/api/summary')
@login_required
def api_summary():
    month=month_bounds(request.args.get('month',current_month()))
    return jsonify(get_month_summary(session['user_id'],month))


@app.context_processor
def inject_globals():
    return {'current_year': date.today().year, 'current_month_value': current_month()}


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
else:
    init_db()
