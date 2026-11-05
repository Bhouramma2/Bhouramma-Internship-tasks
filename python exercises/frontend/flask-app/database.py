
import sqlite3

def connect_db():
    return sqlite3.connect("workspace booking.db")


def create_tables():
    conn = connect_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    );

    CREATE TABLE IF NOT EXISTS workspaces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        location TEXT
    );

    CREATE TABLE IF NOT EXISTS seats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER,
        seat_number TEXT,
        status TEXT,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        seat_id INTEGER,
        booking_date TEXT,
        status TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (seat_id) REFERENCES seats(id)
    );
    """)

    conn.commit()
    conn.close()
    print("Tables created successfully!")


def add_user():
    conn = connect_db()

    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        ("boru9@gmail.com",)
    ).fetchone()

    if user:
        print("User already exists!")
    else:
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            ("Boru", "boru9@gmail.com", "54321")
        )
        conn.commit()
        print("User added successfully!")

    conn.close()


def view_users():
    conn = connect_db()

    users = conn.execute("SELECT * FROM users").fetchall()

    for user in users:
        print(user)

    conn.close()


def add_new_user():
    conn = connect_db()

    name = input("Enter name: ")
    email = input("Enter email: ")
    password = input("Enter password: ")

    try:
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )

        conn.commit()
        print("User added successfully!")

    except sqlite3.IntegrityError:
        print("Email already exists!")

    conn.close()


def update_user():
    conn = connect_db()

    user_id = int(input("Enter user ID: "))
    new_name = input("Enter new name: ")

    conn.execute(
        "UPDATE users SET name = ? WHERE id = ?",
        (new_name, user_id)
    )

    conn.commit()
    print("User updated successfully!")

    conn.close()


def delete_user():
    conn = connect_db()

    user_id = int(input("Enter user ID to delete: "))

    conn.execute(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )

    conn.commit()
    print("User deleted successfully!")

    conn.close()


if __name__ == "__main__":
    create_tables()
    add_user()
    add_new_user()
    update_user()
    delete_user()
    view_users()



