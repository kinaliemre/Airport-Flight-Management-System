import sqlite3
from click import command, echo
from pathlib import Path

from flask import current_app, g
from werkzeug.security import check_password_hash, generate_password_hash


class DatabaseError(RuntimeError):
    pass


def get_db():
    if "db" not in g:
        try:
            g.db = sqlite3.connect(current_app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as error:
            raise DatabaseError("Veritabanı bağlantısı kurulamadı.") from error

    return g.db


def close_db(_error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    try:
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'pilot')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS pilots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                rank TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS aircrafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                model TEXT NOT NULL,
                capacity INTEGER NOT NULL CHECK (capacity > 0),
                seat_info TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE (user_id, name)
            );

            CREATE TABLE IF NOT EXISTS airports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                country TEXT NOT NULL,
                iata_code TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE (user_id, iata_code)
            );

            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                departure_airport_id INTEGER NOT NULL,
                destination_airport_id INTEGER NOT NULL,
                estimated_duration_minutes INTEGER NOT NULL CHECK (estimated_duration_minutes > 0),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (departure_airport_id) REFERENCES airports (id) ON DELETE CASCADE,
                FOREIGN KEY (destination_airport_id) REFERENCES airports (id) ON DELETE CASCADE,
                CHECK (departure_airport_id != destination_airport_id),
                UNIQUE (user_id, departure_airport_id, destination_airport_id)
            );
            """
        )
        db.commit()
    except sqlite3.Error as error:
        db = g.get("db")
        if db is not None:
            db.rollback()
        raise DatabaseError("Veritabanı tabloları oluşturulamadı.") from error


@command("init-db")
def init_db_command():
    init_db()
    echo("Veritabanı tabloları hazır.")


def init_app(app):
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    with app.app_context():
        init_db()

    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


def create_user(full_name, username, password, role, rank=None):
    db = get_db()

    try:
        cursor = db.execute(
            """
            INSERT INTO users (full_name, username, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (full_name, username, generate_password_hash(password), role),
        )

        if role == "pilot":
            db.execute(
                "INSERT INTO pilots (user_id, rank) VALUES (?, ?)",
                (cursor.lastrowid, rank),
            )

        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        db.rollback()
        return None


def create_admin(full_name, username, password):
    return create_user(full_name, username, password, role="admin")


def create_pilot(full_name, username, password, rank):
    return create_user(full_name, username, password, role="pilot", rank=rank)


def get_user_by_id(user_id):
    return get_db().execute(
        """
        SELECT id, full_name, username, role, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


def get_pilot_by_user_id(user_id):
    return get_db().execute(
        """
        SELECT
            pilots.id AS pilot_id,
            pilots.rank,
            users.id AS user_id,
            users.full_name,
            users.username,
            users.created_at
        FROM pilots
        JOIN users ON users.id = pilots.user_id
        WHERE pilots.user_id = ?
        """,
        (user_id,),
    ).fetchone()


def create_aircraft(user_id, name, model, capacity, seat_info):
    db = get_db()

    try:
        cursor = db.execute(
            """
            INSERT INTO aircrafts (user_id, name, model, capacity, seat_info)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, model, capacity, seat_info),
        )
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        db.rollback()
        return None


def get_aircraft_by_id(aircraft_id, user_id):
    return get_db().execute(
        """
        SELECT id, user_id, name, model, capacity, seat_info, is_active, created_at
        FROM aircrafts
        WHERE id = ? AND user_id = ?
        """,
        (aircraft_id, user_id),
    ).fetchone()


def list_aircrafts(user_id):
    return get_db().execute(
        """
        SELECT id, name, model, capacity, seat_info, is_active, created_at
        FROM aircrafts
        WHERE user_id = ?
        ORDER BY name
        """,
        (user_id,),
    ).fetchall()


def create_airport(user_id, name, city, country, iata_code):
    db = get_db()

    try:
        cursor = db.execute(
            """
            INSERT INTO airports (user_id, name, city, country, iata_code)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, city, country, iata_code.upper()),
        )
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        db.rollback()
        return None


def get_airport_by_id(airport_id, user_id):
    return get_db().execute(
        """
        SELECT id, user_id, name, city, country, iata_code, created_at
        FROM airports
        WHERE id = ? AND user_id = ?
        """,
        (airport_id, user_id),
    ).fetchone()


def list_airports(user_id):
    return get_db().execute(
        """
        SELECT id, name, city, country, iata_code, created_at
        FROM airports
        WHERE user_id = ?
        ORDER BY city, name
        """,
        (user_id,),
    ).fetchall()


def create_route(
    user_id, departure_airport_id, destination_airport_id, estimated_duration_minutes
):
    db = get_db()

    departure = get_airport_by_id(departure_airport_id, user_id)
    destination = get_airport_by_id(destination_airport_id, user_id)
    if departure is None or destination is None:
        return None

    try:
        cursor = db.execute(
            """
            INSERT INTO routes (
                user_id,
                departure_airport_id,
                destination_airport_id,
                estimated_duration_minutes
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                departure_airport_id,
                destination_airport_id,
                estimated_duration_minutes,
            ),
        )
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        db.rollback()
        return None


def list_routes(user_id):
    return get_db().execute(
        """
        SELECT
            routes.id,
            routes.estimated_duration_minutes,
            departure.name AS departure_airport,
            departure.city AS departure_city,
            departure.iata_code AS departure_iata,
            destination.name AS destination_airport,
            destination.city AS destination_city,
            destination.iata_code AS destination_iata
        FROM routes
        JOIN airports AS departure ON departure.id = routes.departure_airport_id
        JOIN airports AS destination ON destination.id = routes.destination_airport_id
        WHERE routes.user_id = ?
        ORDER BY departure.city, destination.city
        """,
        (user_id,),
    ).fetchall()


def get_user_for_login(username, role):
    return get_db().execute(
        """
        SELECT users.*, pilots.rank
        FROM users
        LEFT JOIN pilots ON pilots.user_id = users.id
        WHERE users.username = ? AND users.role = ?
        """,
        (username, role),
    ).fetchone()


def verify_user_password(user, password):
    return user is not None and check_password_hash(user["password_hash"], password)
