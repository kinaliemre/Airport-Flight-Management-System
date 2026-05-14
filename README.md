# Airport Flight Management System

Multi-user airport flight management system built with Flask and SQLite.

## Features

- Admin and pilot authentication
- Aircraft, pilot and flight management
- Airport and route management for complete demo flow
- Full CRUD coverage on aircraft records
- Flight schedule conflict validation for pilots and aircraft
- Pilot dashboard with assigned flights
- Pilot cancellation requests
- Admin cancellation request review

## Requirements

- Python 3.11 or newer
- Flask 3.0.3

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run The App

Start the Flask development server:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

You can also use `start_app.bat` on Windows.

## Database

The application uses SQLite. By default, the database is created at:

```text
instance/airport.sqlite
```

To use a different database file, set `AIRPORT_DATABASE` before starting the app:

```powershell
$env:AIRPORT_DATABASE="instance/dev_airport.sqlite"
python app.py
```

Tables are created automatically when the Flask app starts.

## Run Tests

The tests use Python's built-in `unittest` module and temporary SQLite databases.
They focus on business logic and database helper functions, not web routes.

```powershell
python -m unittest
```

Current test coverage includes:

- Admin registration and login
- Pilot registration and login
- Invalid login handling
- Aircraft create, read, update and delete logic
- Airport and route creation/update logic
- Pilot schedule conflict checks
- Aircraft schedule conflict checks
- Flight update conflict checks

## Project Structure

```text
airport_app/
  __init__.py      Flask app factory
  admin.py         Admin routes
  auth.py          Authentication and pilot routes
  db.py            SQLite schema and data functions
templates/         Jinja templates
static/css/        Application styles
tests/             unittest test suite
app.py             Application entry point
```
