from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import re
import logging
import phonenumbers
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_name TEXT NOT NULL,
            location TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER NOT NULL,
            seat_number TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            gender_section TEXT DEFAULT 'Male',
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            seat_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            status TEXT DEFAULT 'Booked',
            name TEXT,
            email TEXT,
            phone_number TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (seat_id) REFERENCES seats(id)
        )
    """)

    # Add missing columns to an existing bookings table
    booking_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(bookings)").fetchall()
    }

    if "name" not in booking_columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN name TEXT")

    if "email" not in booking_columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN email TEXT")

    if "phone_number" not in booking_columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN phone_number TEXT")

    # Prevent duplicate seat numbers in one workspace
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS unique_workspace_seat
        ON seats(workspace_id, seat_number)
    """)

    # Prevent multiple active bookings for one seat
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_booking_per_seat
        ON bookings(seat_id)
        WHERE status = 'Booked'
    """)

    conn.commit()
    conn.close()
    logging.info("Database tables checked successfully.")


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

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
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
            flash("Registration successful. Please login.")

        except sqlite3.IntegrityError:
            conn.rollback()
            flash("Email already registered.")

        finally:
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


 #---------------- LOGIN ----------------

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = connect_db()
        try:
            user = conn.execute("""
                SELECT *
                FROM users
                WHERE email = ?
            """, (email,)).fetchone()
        finally:
            conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

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
    try:
        workspaces = conn.execute("""
            SELECT *
            FROM workspaces
            ORDER BY id DESC
        """).fetchall()
    finally:
        conn.close()

    return render_template("admin_workspaces.html", workspaces=workspaces)


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
    try:
        conn.execute("""
            INSERT INTO workspaces (workspace_name, location)
            VALUES (?, ?)
        """, (workspace_name, location))

        conn.commit()
        flash("Workspace added successfully!")

    except sqlite3.Error:
        conn.rollback()
        logging.exception("Unable to add workspace.")
        flash("Unable to add workspace.")

    finally:
        conn.close()

    return redirect(url_for("admin_workspaces"))
# ---------------- WORKSPACES ----------------

@app.route("/workspaces")
def workspaces():
    if "user_id" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    conn = connect_db()

    try:
        workspace_list = conn.execute("""
            SELECT
                w.*,
                COUNT(s.id) AS total_seats,
                COALESCE(
                    SUM(CASE WHEN s.status = 'Available' THEN 1 ELSE 0 END),
                    0
                ) AS available_seats,
                COALESCE(
                    SUM(CASE WHEN s.status = 'Booked' THEN 1 ELSE 0 END),
                    0
                ) AS booked_seats
            FROM workspaces w
            LEFT JOIN seats s ON w.id = s.workspace_id
            WHERE w.workspace_name LIKE ?
               OR w.location LIKE ?
            GROUP BY w.id
            ORDER BY w.id
        """, (f"%{search}%", f"%{search}%")).fetchall()

    finally:
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
    try:
        workspace = conn.execute("""
            SELECT *
            FROM workspaces
            WHERE id = ?
        """, (workspace_id,)).fetchone()
    finally:
        conn.close()

    if workspace is None:
        flash("Workspace not found.")
        return redirect(url_for("workspaces"))

    return render_template("workspace_details.html", workspace=workspace)


# ---------------- DISPLAY SEATS ----------------

@app.route("/workspace/<int:workspace_id>/seats")
def display_seats(workspace_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    try:
        workspace = conn.execute("""
            SELECT *
            FROM workspaces
            WHERE id = ?
        """, (workspace_id,)).fetchone()

        if workspace is None:
            flash("Workspace not found.")
            return redirect(url_for("workspaces"))

        # Display only active seats
        seats = conn.execute("""
            SELECT id, seat_number, status, workspace_id, gender_section
            FROM seats
            WHERE workspace_id = ?
              AND status != 'Inactive'
            ORDER BY gender_section, seat_number
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

        return render_template(
            "seats.html",
            workspace=workspace,
            seats=seats,
            total_seats=total_seats,
            available_seats=available_seats,
            booked_seats=booked_seats
        )

    except sqlite3.Error:
        logging.exception("Unable to display seats.")
        flash("Unable to load seats.")
        return redirect(url_for("workspaces"))

    finally:
        conn.close()


# ---------------- BOOKING DETAILS PAGE ----------------

@app.route("/booking-details/<int:seat_id>")
def booking_details(seat_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    try:
        seat = conn.execute("""
            SELECT
                seats.*,
                workspaces.workspace_name,
                workspaces.location
            FROM seats
            JOIN workspaces ON seats.workspace_id = workspaces.id
            WHERE seats.id = ?
        """, (seat_id,)).fetchone()

        user = conn.execute("""
            SELECT name, email
            FROM users
            WHERE id = ?
        """, (session["user_id"],)).fetchone()

        if seat is None:
            flash("Seat not found.")
            return redirect(url_for("workspaces"))

        if seat["status"] != "Available":
            flash("This seat is not available.")
            return redirect(url_for(
                "display_seats",
                workspace_id=seat["workspace_id"]
            ))

        return render_template(
            "booking_details.html",
            seat=seat,
            user=user
        )

    finally:
        conn.close()
        
# ---------------- BOOK SEAT ----------------

@app.route("/book-seat/<int:seat_id>", methods=["POST"])
def book_seat(seat_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone_number = request.form.get("phone_number", "").strip()

    if not name or not email or not phone_number:
        flash("Please fill all fields.")
        return redirect(url_for("booking_details", seat_id=seat_id))

    # Validate email
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        flash("Enter a valid email address.")
        return redirect(url_for("booking_details", seat_id=seat_id))

    # Validate international phone number
    try:
        phone = phonenumbers.parse(phone_number, None)

        if not phonenumbers.is_valid_number(phone):
            flash("Please enter a valid phone number.")
            return redirect(url_for("booking_details", seat_id=seat_id))

        phone_number = phonenumbers.format_number(
            phone,
            phonenumbers.PhoneNumberFormat.E164
        )

    except phonenumbers.NumberParseException:
        flash("Enter phone number with country code.")
        return redirect(url_for("booking_details", seat_id=seat_id))

    conn = connect_db()
    workspace_id = None

    try:
        conn.execute("BEGIN IMMEDIATE")

        # Check seat
        seat = conn.execute("""
            SELECT *
            FROM seats
            WHERE id = ?
        """, (seat_id,)).fetchone()

        if seat is None:
            conn.rollback()
            flash("Seat not found.")
            return redirect(url_for("workspaces"))

        workspace_id = seat["workspace_id"]

        if seat["status"] != "Available":
            conn.rollback()
            flash("This seat is not available.")
            return redirect(url_for(
                "display_seats",
                workspace_id=workspace_id
            ))

        # Update seat status
        cursor = conn.execute("""
            UPDATE seats
            SET status = 'Booked'
            WHERE id = ? AND status = 'Available'
        """, (seat_id,))

        if cursor.rowcount != 1:
            conn.rollback()
            flash("Seat is no longer available.")
            return redirect(url_for(
                "display_seats",
                workspace_id=workspace_id
            ))

        # Insert booking details
        booking_cursor = conn.execute("""
            INSERT INTO bookings (
                user_id, seat_id, booking_date, status,
                name, email, phone_number
            )
            VALUES (?, ?, ?, 'Booked', ?, ?, ?)
        """, (
            session["user_id"],
            seat_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            name,
            email,
            phone_number
        ))

        booking_id = booking_cursor.lastrowid

        # Get booking details
        booking = conn.execute("""
            SELECT
                b.id AS booking_id,
                b.name,
                b.email,
                b.phone_number,
                b.booking_date,
                b.status,
                s.seat_number,
                s.workspace_id,
                w.workspace_name,
                w.location
            FROM bookings b
            JOIN seats s ON b.seat_id = s.id
            JOIN workspaces w ON s.workspace_id = w.id
            WHERE b.id = ?
        """, (booking_id,)).fetchone()

        if booking is None:
            raise sqlite3.DatabaseError(
                "Booking details could not be loaded."
            )

        conn.commit()
        flash("Seat booked successfully!")

        return render_template(
            "booking_success.html",
            booking=booking
        )

    except sqlite3.IntegrityError as e:
        conn.rollback()
        logging.exception("Booking database integrity error")
        flash("This seat already has a booking: " + str(e))

        if workspace_id is not None:
            return redirect(url_for(
                "display_seats",
                workspace_id=workspace_id
            ))

        return redirect(url_for("workspaces"))

    except Exception as e:
        conn.rollback()
        logging.exception("Booking failed")
        flash("Booking failed: " + str(e))
        return redirect(url_for("workspaces"))

    finally:
        conn.close()


# ---------------- MY BOOKINGS ----------------

@app.route("/my-bookings")
def my_bookings():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = connect_db()

    try:
        bookings = conn.execute("""
            SELECT
                b.id AS booking_id,
                b.name,
                b.email,
                b.phone_number,
                b.booking_date,
                b.status,
                s.seat_number,
                w.workspace_name,
                w.location
            FROM bookings b
            JOIN seats s ON b.seat_id = s.id
            JOIN workspaces w ON s.workspace_id = w.id
            WHERE b.user_id = ?
            ORDER BY b.id DESC
        """, (session["user_id"],)).fetchall()

    finally:
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
        conn.execute("BEGIN IMMEDIATE")

        booking = conn.execute("""
            SELECT *
            FROM bookings
            WHERE id = ?
              AND user_id = ?
              AND status = 'Booked'
        """, (booking_id, session["user_id"])).fetchone()

        if booking is None:
            conn.rollback()
            flash("Booking not found or already cancelled.")
            return redirect(url_for("my_bookings"))

        conn.execute("""
            UPDATE bookings
            SET status = 'Cancelled'
            WHERE id = ?
              AND user_id = ?
              AND status = 'Booked'
        """, (booking_id, session["user_id"]))

        conn.execute("""
            UPDATE seats
            SET status = 'Available'
            WHERE id = ?
        """, (booking["seat_id"],))

        conn.commit()
        flash("Booking cancelled successfully.")

    except sqlite3.Error:
        conn.rollback()
        logging.exception("Unable to cancel booking.")
        flash("Unable to cancel booking. Please try again.")

    finally:
        conn.close()

    return redirect(url_for("my_bookings"))

# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") != "admin":
        return "403 Forbidden - Admin access only", 403

    conn = connect_db()

    try:
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

    finally:
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

    # Check whether user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Check whether user is admin
    if session.get("user_role") != "admin":
        return "403 Forbidden - Admin access only", 403

    conn = connect_db()

    try:
        seats = conn.execute("""
            SELECT
                seats.id,
                seats.seat_number,
                seats.status,
                seats.workspace_id,
                seats.gender_section,
                workspaces.workspace_name
            FROM seats
            JOIN workspaces ON seats.workspace_id = workspaces.id
            ORDER BY seats.id DESC
        """).fetchall()

        workspaces = conn.execute("""
            SELECT *
            FROM workspaces
        """).fetchall()

    finally:
        conn.close()

    return render_template(
        "admin_seats.html",
        seats=seats,
        workspaces=workspaces
    )

# ---------------- ADD ADMIN SEAT ----------------

@app.route("/admin/seats/add", methods=["POST"])
def add_admin_seat():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Check admin role
    if session.get("user_role") != "admin":
        return "403 Forbidden - Admin access only", 403

    seat_number = request.form.get("seat_number", "").strip()
    workspace_id = request.form.get("workspace_id", "").strip()
    gender_section = request.form.get("gender_section", "")

    if not seat_number or not workspace_id or gender_section not in ["Male", "Female"]:
        flash("Please fill all fields correctly.")
        return redirect(url_for("admin_seats"))

    conn = connect_db()

    try:
        conn.execute("""
            INSERT INTO seats (
                workspace_id, seat_number, status, gender_section
            )
            VALUES (?, ?, 'Available', ?)
        """, (workspace_id, seat_number, gender_section))

        conn.commit()
        flash("Seat added successfully!")

    except sqlite3.IntegrityError:
        conn.rollback()
        flash("Seat number already exists in this workspace.")

    except sqlite3.Error:
        conn.rollback()
        logging.exception("Unable to add seat.")
        flash("Unable to add seat.")

    finally:
        conn.close()

    return redirect(url_for("admin_seats"))

# ---------------- UPDATE SEAT ----------------
# ---------------- UPDATE SEAT ----------------

@app.route("/admin/seats/update/<int:seat_id>", methods=["POST"])
def update_admin_seat(seat_id):

    # Check whether user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Check whether user is admin
    if session.get("user_role") != "admin":
        return "403 Forbidden - Admin access only", 403

    seat_number = request.form.get("seat_number", "").strip()
    workspace_id = request.form.get("workspace_id", "").strip()
    gender_section = request.form.get("gender_section", "")

    if not seat_number or not workspace_id or gender_section not in ["Male", "Female"]:
        return "Please fill all fields correctly"

    conn = connect_db()

    try:
        seat = conn.execute(
            "SELECT status FROM seats WHERE id = ?",
            (seat_id,)
        ).fetchone()

        if seat is None:
            return "Seat not found"

        if seat["status"] != "Available":
            return "Only available seats can be updated"

        conn.execute("""
            UPDATE seats
            SET seat_number = ?, workspace_id = ?, gender_section = ?
            WHERE id = ?
        """, (seat_number, workspace_id, gender_section, seat_id))

        conn.commit()
        flash("Seat updated successfully!")
        return redirect(url_for("admin_seats"))

    except sqlite3.IntegrityError:
        conn.rollback()
        return "Seat number already exists in this workspace"

    finally:
        conn.close()


# ---------------- DEACTIVATE SEAT ----------------

@app.route("/admin/seats/deactivate/<int:seat_id>", methods=["POST"])
def deactivate_admin_seat(seat_id):

    # Check whether user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Check whether user is admin
    if session.get("user_role") != "admin":
        return "403 Forbidden - Admin access only", 403

    conn = connect_db()

    try:
        seat = conn.execute(
            "SELECT status FROM seats WHERE id = ?",
            (seat_id,)
        ).fetchone()

        if seat is None:
            return "Seat not found"

        if seat["status"] == "Booked":
            return "Cannot deactivate a booked seat"

        conn.execute("""
            UPDATE seats
            SET status = 'Inactive'
            WHERE id = ?
        """, (seat_id,))

        conn.commit()
        flash("Seat deactivated successfully!")
        return redirect(url_for("admin_seats"))

    finally:
        conn.close()

# ---------------- ERROR HANDLERS ----------------

@app.errorhandler(404)
def page_not_found(error):
    logging.warning("Page not found: %s", request.path)
    return "Page Not Found", 404


@app.errorhandler(500)
def server_error(error):
    logging.exception("Internal Server Error")
    return "Something went wrong. Check app.log for details.", 500


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    create_table()
    app.run(debug=False)


