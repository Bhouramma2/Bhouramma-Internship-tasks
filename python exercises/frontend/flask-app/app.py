from flask import Flask, request
import sqlite3

app = Flask(__name__)

# Database connection
def connect_db():
    conn = sqlite3.connect("users.db")
    return conn

# Create users table
def create_table():
    conn = connect_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            password TEXT
        )
    """)

    conn.commit()
    conn.close()

# Home page
@app.route("/")
def home():
    return "Welcome to my application"

# Registration API
@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    conn = connect_db()

    conn.execute(
        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
        (name, email, password)
    )

    conn.commit()
    conn.close()

    return "Registration successful"

# Login API
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    conn = connect_db()

    user = conn.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (email, password)
    ).fetchone()

    conn.close()

    if user:
        return "Login successful"
    else:
        return "Invalid email or password"

# Create table
create_table()

app.run()
