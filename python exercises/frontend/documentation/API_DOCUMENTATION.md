# Book My Seat – API Documentation

## 1. Introduction

This document describes the routes used in the Book My Seat Flask application.

The application uses Flask routes to handle user registration, login, workspace management, seat booking, and administrator operations.

## 2. User Routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Opens the home page or redirects users |
| `/register` | GET, POST | Registers a new user |
| `/login` | GET, POST | Logs in an existing user |
| `/logout` | GET | Logs out the user |
| `/dashboard` | GET | Displays the user dashboard |
| `/workspaces` | GET | Displays available workspaces |
| `/workspace/<workspace_id>` | GET | Displays workspace details |
| `/workspace/<workspace_id>/seats` | GET | Displays seats in a workspace |

## 3. Booking Routes

| Route | Method | Purpose |
|---|---|---|
| `/booking-details/<seat_id>` | GET | Displays the booking form |
| `/book-seat/<seat_id>` | POST | Books the selected seat |
| `/my-bookings` | GET | Displays the user's bookings |
| `/cancel-booking/<booking_id>` | POST | Cancels a booking |

## 4. Administrator Routes

| Route | Method | Purpose |
|---|---|---|
| `/admin` | GET | Displays the admin dashboard |
| `/admin/workspaces` | GET | Displays workspace management |
| `/admin/add_workspace` | POST | Adds a workspace |
| `/admin/seats` | GET | Displays seat management |
| `/admin/seats/add` | POST | Adds a seat |
| `/admin/seats/update/<seat_id>` | POST | Updates a seat |
| `/admin/seats/deactivate/<seat_id>` | POST | Deactivates a seat |

## 5. Access Control

The application uses session-based authentication and role-based authorization.

- Unauthenticated users are redirected to the login page for protected pages.
- Normal users cannot access admin-only pages.
- Administrators can access protected admin functionality.
- Unauthorized admin requests receive a 403 Forbidden response.

## 6. Database

The application uses SQLite to store information.

Main database tables:

- `users` – Stores user account details and roles.
- `workspaces` – Stores workspace information.
- `seats` – Stores seat details and availability.
- `bookings` – Stores booking information.

## 7. Testing

Unit tests are available in the `tests/` folder.

Run the tests using:

```bash
python -m unittest discover -s tests -t . -v
```

The current test suite contains 10 test cases, and all 10 passed in the latest execution.

## 8. Conclusion

The Book My Seat application provides workspace booking functionality with user authentication, seat management, administrator access control, and automated testing.
