from flask import Flask, request, session, redirect, render_template, abort
import sqlite3
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "change_this_to_a_random_secret_key"


# Database connection
def connect_db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


# Create database tables
def create_table():
    conn = connect_db()

    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Workspaces table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_name TEXT NOT NULL,
            location TEXT NOT NULL
        )
    """)

    # Add sample workspaces if the table is empty
    count = conn.execute(
        "SELECT COUNT(*) FROM workspaces"
    ).fetchone()[0]

    if count == 0:
        conn.executemany(
            """
            INSERT INTO workspaces (workspace_name, location)
            VALUES (?, ?)
            """,
            [
                ("Tech Workspace", "Bangalore"),
                ("Training Room", "Belagavi"),
                ("Meeting Room", "Mysore")
            ]
        )

    conn.commit()
    conn.close()


# Home page
@app.route("/")
def home():
    return "Welcome to my application"


# User registration
@app.route("/register", methods=["POST"])
def register():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return "All fields are required"

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return "Please enter a valid email"

    if len(password) < 6:
        return "Password must contain at least 6 characters"

    conn = connect_db()

    user = conn.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if user:
        conn.close()
        return "Email already registered"

    hashed_password = generate_password_hash(password)

    conn.execute(
        """
        INSERT INTO users (name, email, password)
        VALUES (?, ?, ?)
        """,
        (name, email, hashed_password)
    )

    conn.commit()
    conn.close()

    return "Registration successful"


# User login
@app.route("/login", methods=["POST"])
def login():

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return "Email and password are required"

    conn = connect_db()

    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]

        return redirect("/dashboard")

    return "Invalid email or password"


# Protected dashboard
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return "Please login first", 401

    return "Welcome " + session["user_name"] + "! You are logged in."


# User logout
@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return "Logout successful"


# DAY 6 - Workspace listing, search and filter
@app.route("/workspaces")
def workspaces():

    search = request.args.get("search", "").strip()
    location = request.args.get("location", "").strip()

    conn = connect_db()

    query = "SELECT * FROM workspaces WHERE 1=1"
    values = []

    # Search by workspace name
    if search:
        query += " AND workspace_name LIKE ?"
        values.append("%" + search + "%")

    # Filter by location
    if location:
        query += " AND location = ?"
        values.append(location)

    workspace_list = conn.execute(
        query, values
    ).fetchall()

    locations = conn.execute(
        "SELECT DISTINCT location FROM workspaces"
    ).fetchall()

    conn.close()

    return render_template(
        "workspaces.html",
        workspaces=workspace_list,
        locations=locations,
        search=search,
        selected_location=location
    )


# DAY 6 - Workspace details
@app.route("/workspace/<int:workspace_id>")
def workspace_details(workspace_id):

    conn = connect_db()

    workspace = conn.execute(
        "SELECT * FROM workspaces WHERE id = ?",
        (workspace_id,)
    ).fetchone()

    conn.close()

    if workspace is None:
        abort(404)

    return render_template(
        "workspace_details.html",
        workspace=workspace
    )


if __name__ == "__main__":
    create_table()
    app.run(debug=True)






