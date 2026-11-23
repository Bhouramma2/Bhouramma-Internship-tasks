
import unittest
import tempfile
import os
import app as application


class BookMySeatTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_database = application.DATABASE

        application.DATABASE = os.path.join(
            self.temp_dir.name, "test.db"
        )

        application.app.config["TESTING"] = True
        self.client = application.app.test_client()

        application.create_table()

    def tearDown(self):
        application.DATABASE = self.old_database
        self.temp_dir.cleanup()

    # TEST 1: Home page redirect
    def test_home_redirect(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)

    # TEST 2: User registration
    def test_user_registration(self):
        response = self.client.post("/register", data={
            "name": "Test User",
            "email": "test@example.com",
            "password": "test123"
        })

        self.assertEqual(response.status_code, 302)

    # TEST 3: User login
    def test_user_login(self):
        self.client.post("/register", data={
            "name": "Test User",
            "email": "test@example.com",
            "password": "test123"
        })

        response = self.client.post("/login", data={
            "email": "test@example.com",
            "password": "test123"
        })

        self.assertEqual(response.status_code, 302)

    # TEST 4: Invalid login
    def test_invalid_login(self):
        response = self.client.post("/login", data={
            "email": "wrong@example.com",
            "password": "wrong123"
        })

        self.assertEqual(response.status_code, 200)

    # TEST 5: Workspace requires login
    def test_workspace_requires_login(self):
        response = self.client.get("/workspaces")
        self.assertEqual(response.status_code, 302)

    # Helper: Create test user, workspace and seat
    def create_test_seat(self):

        self.client.post("/register", data={
            "name": "Test User",
            "email": "test@example.com",
            "password": "test123"
        })

        self.client.post("/login", data={
            "email": "test@example.com",
            "password": "test123"
        })

        conn = application.connect_db()

        cursor = conn.execute("""
            INSERT INTO workspaces (workspace_name, location)
            VALUES (?, ?)
        """, ("Test Workspace", "Bengaluru"))

        workspace_id = cursor.lastrowid

        cursor = conn.execute("""
            INSERT INTO seats
            (workspace_id, seat_number, status, gender_section)
            VALUES (?, ?, ?, ?)
        """, (workspace_id, "T1", "Available", "Male"))

        seat_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return seat_id

    # TEST 6: Successful seat booking
    def test_successful_seat_booking(self):

        seat_id = self.create_test_seat()

        response = self.client.post(
            f"/book-seat/{seat_id}",
            data={
                "name": "Test User",
                "email": "test@example.com",
                "phone_number": "+919876543210"
            }
        )

        conn = application.connect_db()

        seat = conn.execute(
            "SELECT status FROM seats WHERE id = ?",
            (seat_id,)
        ).fetchone()

        booking = conn.execute(
            "SELECT * FROM bookings WHERE seat_id = ?",
            (seat_id,)
        ).fetchone()

        conn.close()

        self.assertEqual(seat["status"], "Booked")
        self.assertIsNotNone(booking)

    # TEST 7: Duplicate booking prevention
    def test_duplicate_booking(self):

        seat_id = self.create_test_seat()

        booking_data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone_number": "+919876543210"
        }

        self.client.post(
            f"/book-seat/{seat_id}",
            data=booking_data
        )

        self.client.post(
            f"/book-seat/{seat_id}",
            data=booking_data
        )

        conn = application.connect_db()

        count = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE seat_id = ?",
            (seat_id,)
        ).fetchone()[0]

        conn.close()

        self.assertEqual(count, 1)

    # TEST 8: Cancel booking
    def test_cancel_booking(self):

        seat_id = self.create_test_seat()

        self.client.post(
            f"/book-seat/{seat_id}",
            data={
                "name": "Test User",
                "email": "test@example.com",
                "phone_number": "+919876543210"
            }
        )

        conn = application.connect_db()

        booking = conn.execute(
            "SELECT id FROM bookings WHERE seat_id = ?",
            (seat_id,)
        ).fetchone()

        conn.close()

        self.assertIsNotNone(booking)

        self.client.post(
            f"/cancel-booking/{booking['id']}"
        )

        conn = application.connect_db()

        seat = conn.execute(
            "SELECT status FROM seats WHERE id = ?",
            (seat_id,)
        ).fetchone()

        booking_status = conn.execute(
            "SELECT status FROM bookings WHERE id = ?",
            (booking["id"],)
        ).fetchone()

        conn.close()

        self.assertEqual(seat["status"], "Available")
        self.assertEqual(booking_status["status"], "Cancelled")


# TEST 9: Admin page requires login
    def test_admin_requires_login(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 302)



            # TEST 10: Normal user should not access admin page
    def test_normal_user_cannot_access_admin(self):

        self.client.post("/register", data={
            "name": "Normal User",
            "email": "normal@example.com",
            "password": "test123"
        })

        self.client.post("/login", data={
            "email": "normal@example.com",
            "password": "test123"
        })

        response = self.client.get("/admin")

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
