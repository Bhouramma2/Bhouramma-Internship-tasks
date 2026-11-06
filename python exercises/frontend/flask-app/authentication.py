
from flask import Flask, request, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "12345"


@app.route("/")
def home():
    return "Authentication Application is Running!"

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name","").strip()
    email = request.form.get("email", "").strip()
    password =request.form.get("password", "")

    if not name or not email or not password:
        return "Please fill all fields", 400

    if "@" not in email:
        return "Enter a valid email", 400

    password = generate_password_hash(password)

    with sqlite3.connect("users.db") as db:
        db.execute("INSERT INTO users VALUES (NULL,?,?,?)",
                   (name, email, password))
    return "Registered successfully"

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return "Please enter email and password", 400

    with sqlite3.connect("users.db") as db:
        user = db.execute(
            "SELECT id,password FROM users WHERE email=?", (email,)
        ).fetchone()

    if user and check_password_hash(user[1], password):
        session["user"] = user[0]
        return "Login successful"
    return "Invalid login"

@app.route("/profile")
def profile():
    return "Welcome!" if "user" in session else "Please login"

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return "Logged out"

if __name__ == "__main__":
    app.run(port=5001, debug=True)




