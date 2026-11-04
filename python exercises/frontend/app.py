from flask import Flask, request
import sqlite3

app = Flask(__name__)

DATABASE = "users.db"


def get_connection():
    return sqlite3.connect(DATABASE)


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)


@app.route("/")
def home():
    return "Welcome to Student Login Application"


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return "Please fill all fields", 400

    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password)
            )

        return "Registration successful"

    except sqlite3.IntegrityError:
        return "Email already registered", 409


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return "Please enter email and password", 400

    with get_connection() as conn:
        result = conn.execute(
            "SELECT id FROM users WHERE email = ? AND password = ?",
            (email, password)
        ).fetchone()

    if result:
        return "Login successful"

    return "Invalid email or password", 401


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)