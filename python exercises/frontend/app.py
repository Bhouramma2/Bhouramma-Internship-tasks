from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import re
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "workspace_booking_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "users.db")

logging.basicConfig(
    filename=os.path.join(BASE_DIR, "app.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ---------------- DATABASE CONNECTION ----------------

def connect_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ---------------- CREATE TABLES ----------------

def create_table():
    conn = connect_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Workspaces table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_name TEXT NOT NULL,
            location TEXT NOT NULL
        )
    """)

    # Add admin role to existing users table
    user_columns = [
        row["name"] for row in cursor.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    ]

    if "role" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN role TEXT DEFAULT 'user'
        """)

    # Add active status to existing workspaces table
    workspace_columns = [
        row["name"] for row in cursor.execute(
            "PRAGMA table_info(workspaces)"
        ).fetchall()
    ]

    if "is_active" not in workspace_columns:
        cursor.execute("""
            ALTER TABLE workspaces
            ADD COLUMN is_active INTEGER DEFAULT 1
        """)

    # Seats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER NOT NULL,
            seat_number TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
        )
    """)

    # Prevent duplicate seats in the same workspace
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS unique_workspace_seat
        ON seats(workspace_id, seat_number)
    """)

    # Bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            seat_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            status TEXT DEFAULT 'Booked',
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (seat_id) REFERENCES seats(id)
        )
    """)

    # Prevent two active bookings for the same seat
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_booking_per_seat
        ON bookings(seat_id)
        WHERE status = 'Booked'
    """)

    # Insert sample workspaces if empty
    workspace_count = cursor.execute(
        "SELECT COUNT(*) FROM workspaces"
    ).fetchone()[0]

    if workspace_count == 0:

        sample_workspaces = [
            ("Tech Workspace", "Bangalore"),
            ("Training Room", "Belagavi"),
            ("Meeting Room", "Mysore")
        ]

        cursor.executemany("""
            INSERT INTO workspaces (workspace_name, location)
            VALUES (?, ?)
        """, sample_workspaces)

    # Insert 5 sample seats for each workspace
    workspaces = cursor.execute(
        "SELECT id FROM workspaces"
    ).fetchall()

    for workspace in workspaces:

        workspace_id = workspace["id"]

        for number in range(1, 6):

            seat_number = f"A{number}"

            cursor.execute("""
                INSERT OR IGNORE INTO seats
                (workspace_id, seat_number, status)
                VALUES (?, ?, 'Available')
            """, (workspace_id, seat_number))

    conn.commit()
    logging.info("User registered successfully")
    conn.close()

# ---------------- HOME PAGE ----------------

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("workspaces"))

    return redirect(url_for("login"))

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill all fields.")
            return redirect(url_for("register"))

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Please enter a valid email address.")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must contain at least 6 characters.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn = connect_db()

        try:

            conn.execute("""
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
            """, (name, email, hashed_password))

            conn.commit()
            logging.info("Seat booked successfully")
            flash("Registration successful. Please login.")

        except sqlite3.IntegrityError:
            conn.rollback()
            logging.warning("Duplicate email registration attempted")
            flash("Email already registered.")

        finally:
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = connect_db()

        user = conn.execute("""
            SELECT * FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("workspaces"))

        flash("Invalid email or password.")

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return redirect(url_for("workspaces"))

# ---------------- ADMIN WORKSPACE PAGE ----------------

@app.route("/admin/workspaces")
def admin_workspaces():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    workspaces = conn.execute("""
        SELECT * FROM workspaces
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_workspaces.html",
        workspaces=workspaces
    )

# ---------------- ADD WORKSPACE ----------------

@app.route("/admin/add_workspace", methods=["POST"])
def add_workspace():

    if "user_id" not in session:
        return redirect(url_for("login"))

    workspace_name = request.form.get("workspace_name", "").strip()
    location = request.form.get("location", "").strip()

    if not workspace_name or not location:
        flash("Please fill all fields.")
        return redirect(url_for("admin_workspaces"))

    conn = connect_db()

    conn.execute("""
        INSERT INTO workspaces (workspace_name, location)
        VALUES (?, ?)
    """, (workspace_name, location))

    conn.commit()
    conn.close()

    flash("Workspace added successfully!")

    return redirect(url_for("admin_workspaces"))

# ---------------- WORKSPACES ----------------

@app.route("/workspaces")
def workspaces():

    if "user_id" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()

    conn = connect_db()

    workspace_list = conn.execute("""
        SELECT
            w.*,
            COUNT(s.id) AS total_seats,

            COALESCE(
                SUM(
                    CASE
                        WHEN s.status = 'Available' THEN 1
                        ELSE 0
                    END
                ), 0
            ) AS available_seats,

            COALESCE(
                SUM(
                    CASE
                        WHEN s.status = 'Booked' THEN 1
                        ELSE 0
                    END
                ), 0
            ) AS booked_seats

        FROM workspaces w

        LEFT JOIN seats s
        ON w.id = s.workspace_id

        WHERE w.workspace_name LIKE ?
        OR w.location LIKE ?

        GROUP BY w.id
        ORDER BY w.id
    """, (f"%{search}%", f"%{search}%")).fetchall()

    conn.close()

    return render_template(
        "workspaces.html",
        workspaces=workspace_list,
        search=search
    )

# ---------------- WORKSPACE DETAILS ----------------

@app.route("/workspace/<int:workspace_id>")
def workspace_details(workspace_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    workspace = conn.execute("""
        SELECT * FROM workspaces
        WHERE id = ?
    """, (workspace_id,)).fetchone()

    conn.close()

    if workspace is None:

        flash("Workspace not found.")

        return redirect(url_for("workspaces"))

    return render_template(
        "workspace_details.html",
        workspace=workspace
    )

# ---------------- DISPLAY SEATS ----------------

@app.route("/workspace/<int:workspace_id>/seats")
def display_seats(workspace_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    workspace = conn.execute("""
        SELECT * FROM workspaces
        WHERE id = ?
    """, (workspace_id,)).fetchone()

    if workspace is None:

        conn.close()
        flash("Workspace not found.")

        return redirect(url_for("workspaces"))

    seats = conn.execute("""
        SELECT * FROM seats
        WHERE workspace_id = ?
        ORDER BY seat_number
    """, (workspace_id,)).fetchall()

    total_seats = len(seats)

    available_seats = sum(
        1 for seat in seats
        if seat["status"] == "Available"
    )

    booked_seats = sum(
        1 for seat in seats
        if seat["status"] == "Booked"
    )

    conn.close()

    return render_template(
        "seats.html",
        workspace=workspace,
        seats=seats,
        total_seats=total_seats,
        available_seats=available_seats,
        booked_seats=booked_seats
    )

# ---------------- BOOK SEAT ----------------

@app.route("/book-seat/<int:seat_id>", methods=["POST"])
def book_seat(seat_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    try:

        # Lock database for this booking transaction
        conn.execute("BEGIN IMMEDIATE")

        seat = conn.execute("""
            SELECT * FROM seats
            WHERE id = ?
        """, (seat_id,)).fetchone()

        if seat is None:

            conn.rollback()
            flash("Seat not found.")

            return redirect(url_for("workspaces"))

        workspace_id = seat["workspace_id"]

        if seat["status"] != "Available":

            conn.rollback()
            flash("This seat is already booked.")

            return redirect(
                url_for(
                    "display_seats",
                    workspace_id=workspace_id
                )
            )

        # Update seat status
        cursor = conn.execute("""
            UPDATE seats
            SET status = 'Booked'
            WHERE id = ?
            AND status = 'Available'
        """, (seat_id,))

        if cursor.rowcount != 1:

            conn.rollback()
            flash("Seat is no longer available.")

            return redirect(
                url_for(
                    "display_seats",
                    workspace_id=workspace_id
                )
            )

        # Insert booking details
        conn.execute("""
            INSERT INTO bookings
            (user_id, seat_id, booking_date, status)
            VALUES (?, ?, ?, 'Booked')
        """, (
            session["user_id"],
            seat_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

        flash("Seat booked successfully.")

        return redirect(
            url_for(
                "display_seats",
                workspace_id=workspace_id
            )
        )

    except sqlite3.IntegrityError:

        conn.rollback()

        flash("This seat is already booked.")

        seat = conn.execute("""
            SELECT workspace_id FROM seats
            WHERE id = ?
        """, (seat_id,)).fetchone()

        if seat:

            return redirect(
                url_for(
                    "display_seats",
                    workspace_id=seat["workspace_id"]
                )
            )

        return redirect(url_for("workspaces"))

    finally:

        conn.close()

# ---------------- MY BOOKINGS ----------------

@app.route("/my-bookings")
def my_bookings():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    bookings = conn.execute("""
        SELECT
            b.id AS booking_id,
            b.booking_date,
            b.status,
            s.seat_number,
            w.workspace_name,
            w.location

        FROM bookings b

        JOIN seats s
        ON b.seat_id = s.id

        JOIN workspaces w
        ON s.workspace_id = w.id

        WHERE b.user_id = ?

        ORDER BY b.id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )

# ---------------- CANCEL BOOKING ----------------

@app.route("/cancel-booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    try:

        # Start transaction
        conn.execute("BEGIN IMMEDIATE")

        booking = conn.execute("""
            SELECT * FROM bookings
            WHERE id = ?
            AND user_id = ?
            AND status = 'Booked'
        """, (
            booking_id,
            session["user_id"]
        )).fetchone()

        if booking is None:

            conn.rollback()

            flash("Booking not found or already cancelled.")

            return redirect(url_for("my_bookings"))

        # Update booking status
        conn.execute("""
            UPDATE bookings
            SET status = 'Cancelled'
            WHERE id = ?
            AND user_id = ?
            AND status = 'Booked'
        """, (
            booking_id,
            session["user_id"]
        ))

        # Make seat available again
        conn.execute("""
            UPDATE seats
            SET status = 'Available'
            WHERE id = ?
        """, (booking["seat_id"],))

        conn.commit()

        flash("Booking cancelled successfully.")

    except sqlite3.Error:

        conn.rollback()

        flash("Unable to cancel booking. Please try again.")

    finally:

        conn.close()

    return redirect(url_for("my_bookings"))


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    total_workspaces = conn.execute(
        "SELECT COUNT(*) FROM workspaces"
    ).fetchone()[0]

    total_seats = conn.execute(
        "SELECT COUNT(*) FROM seats"
    ).fetchone()[0]

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    active_bookings = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE status = 'Booked'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        admin_name=session.get("user_name"),
        total_workspaces=total_workspaces,
        total_seats=total_seats,
        total_users=total_users,
        active_bookings=active_bookings
    )

# ---------------- ADMIN MANAGE SEATS ----------------

@app.route("/admin/seats")
def admin_seats():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    seats = conn.execute("""
        SELECT seats.id,
               seats.seat_number,
               seats.status,
               seats.workspace_id,
               workspaces.workspace_name
        FROM seats
        JOIN workspaces
        ON seats.workspace_id = workspaces.id
        ORDER BY seats.id DESC
    """).fetchall()

    workspaces = conn.execute("""
        SELECT * FROM workspaces
    """).fetchall()

    conn.close()

    return render_template(
        "admin_seats.html",
        seats=seats,
        workspaces=workspaces
    )

# ---------------- ADD NEW SEAT ----------------

@app.route("/admin/seats/add", methods=["POST"])
def add_admin_seat():

    if "user_id" not in session:
        return redirect(url_for("login"))

    seat_number = request.form.get("seat_number")
    workspace_id = request.form.get("workspace_id")

    if not seat_number or not workspace_id:
        return "Please fill all fields"

    conn = connect_db()

    workspace = conn.execute(
        "SELECT id FROM workspaces WHERE id = ?",
        (workspace_id,)
    ).fetchone()

    if workspace is None:
        conn.close()
        return "Workspace not found"

    conn.execute("""
        INSERT INTO seats (workspace_id, seat_number, status)
        VALUES (?, ?, 'Available')
    """, (workspace_id, seat_number))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_seats"))

# ---------------- UPDATE SEAT ----------------

@app.route("/admin/seats/update/<int:seat_id>", methods=["POST"])
def update_admin_seat(seat_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    seat_number = request.form.get("seat_number")
    workspace_id = request.form.get("workspace_id")

    if not seat_number or not workspace_id:
        return "Please fill all fields"

    conn = connect_db()

    seat = conn.execute(
        "SELECT status FROM seats WHERE id = ?",
        (seat_id,)
    ).fetchone()

    if seat is None:
        conn.close()
        return "Seat not found"

    if seat["status"] == "Booked":
        conn.close()
        return "Cannot update a booked seat"

    conn.execute("""
        UPDATE seats
        SET seat_number = ?, workspace_id = ?
        WHERE id = ?
    """, (seat_number, workspace_id, seat_id))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_seats"))

# ---------------- DEACTIVATE SEAT ----------------

@app.route("/admin/seats/deactivate/<int:seat_id>", methods=["POST"])
def deactivate_admin_seat(seat_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    seat = conn.execute(
        "SELECT status FROM seats WHERE id = ?",
        (seat_id,)
    ).fetchone()

    if seat is None:
        conn.close()
        return "Seat not found"

    if seat["status"] == "Booked":
        conn.close()
        return "Cannot deactivate a booked seat"

    conn.execute("""
        UPDATE seats
        SET status = 'Inactive'
        WHERE id = ?
    """, (seat_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_seats"))

# ---------------- RUN APPLICATION ----------------
@app.errorhandler(404)
def page_not_found(error):
    logging.warning("Page not found")
    return "Page Not Found", 404


@app.errorhandler(500)
def server_error(error):
    logging.error("Internal Server Error")
    return "Something went wrong", 500

if __name__ == "__main__":

    create_table()

    app.run(debug=False)


    