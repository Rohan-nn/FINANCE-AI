from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, json, csv, io
from datetime import datetime

app = Flask(__name__)
app.secret_key = "financeai_pro"

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("finance.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        title TEXT,
        amount REAL,
        category TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- LOGIN ----------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("finance.db")
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username,password))
        user = c.fetchone()

        if user:
            session["user_id"] = user[0]
            return redirect("/")
        else:
            c.execute("INSERT INTO users(username,password) VALUES (?,?)",(username,password))
            conn.commit()
            session["user_id"] = c.lastrowid
            return redirect("/")

    return render_template("login.html")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------- DASHBOARD ----------
@app.route("/", methods=["GET","POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("finance.db")
    c = conn.cursor()

    # ---- ADD TRANSACTION ----
    if request.method == "POST":
        t_type = request.form["type"]
        title = request.form["title"]
        amount = float(request.form["amount"])
        category = request.form["category"]
        date = datetime.now().strftime("%d-%m-%Y")

        c.execute("INSERT INTO transactions(user_id,type,title,amount,category,date) VALUES (?,?,?,?,?,?)",
                  (session["user_id"], t_type, title, amount, category, date))
        conn.commit()

    # ---- FETCH DATA ----
    c.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC",(session["user_id"],))
    data = c.fetchall()

    income = sum([d[4] for d in data if d[2]=="income"])
    expense = sum([d[4] for d in data if d[2]=="expense"])
    balance = income - expense

    # ---- CATEGORY CHART ----
    cat = {}
    for d in data:
        if d[2] == "expense":
            cat[d[5]] = cat.get(d[5],0) + d[4]

    labels = list(cat.keys())
    values = list(cat.values())

    # ---- SAVINGS GOAL ----
    savings_goal = income * 0.2 if income else 0

    # ---- MONTHLY BUDGET ----
    safe_budget = income * 0.5 if income else 0

    # ---- AI INSIGHT ----
    if expense > income:
        insight = "⚠ You are spending more than you earn."
    elif safe_budget and expense > safe_budget:
        insight = "⚠ You crossed safe monthly budget."
    elif income == 0:
        insight = "Add income to track financial health."
    else:
        insight = "✔ Your finances look healthy."

    # ---- PREDICTION ----
    prediction = round(expense * 1.1,2) if expense else 0

    conn.close()

    return render_template("dashboard.html",
                           data=data,
                           income=income,
                           expense=expense,
                           balance=balance,
                           labels=json.dumps(labels),
                           values=json.dumps(values),
                           insight=insight,
                           savings_goal=savings_goal,
                           prediction=prediction)
# ---------- EXPORT ----------
@app.route("/export")
def export():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("finance.db")
    c = conn.cursor()
    c.execute("SELECT type,title,amount,category,date FROM transactions WHERE user_id=?",(session["user_id"],))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Type","Title","Amount","Category","Date"])
    writer.writerows(rows)

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()),
                     mimetype="text/csv",
                     as_attachment=True,
                     download_name="finance_report.csv")

@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect("finance.db")
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return redirect("/")
if __name__ == "__main__":
    app.run(debug=True)