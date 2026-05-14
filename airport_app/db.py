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

            CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                flight_number TEXT NOT NULL,
                route_id INTEGER NOT NULL,
                pilot_id INTEGER NOT NULL,
                aircraft_id INTEGER NOT NULL,
                departure_time TEXT NOT NULL,
                arrival_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled'
                    CHECK (status IN ('scheduled', 'delayed', 'cancelled', 'completed')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE,
                FOREIGN KEY (pilot_id) REFERENCES pilots (id) ON DELETE CASCADE,
                FOREIGN KEY (aircraft_id) REFERENCES aircrafts (id) ON DELETE CASCADE,
                CHECK (departure_time < arrival_time),
                UNIQUE (user_id, flight_number)
            );

            CREATE TABLE IF NOT EXISTS cabin_crews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                duty TEXT NOT NULL,
                phone TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS flight_cabin_crews (
                flight_id INTEGER NOT NULL,
                cabin_crew_id INTEGER NOT NULL,
                PRIMARY KEY (flight_id, cabin_crew_id),
                FOREIGN KEY (flight_id) REFERENCES flights (id) ON DELETE CASCADE,
                FOREIGN KEY (cabin_crew_id) REFERENCES cabin_crews (id) ON DELETE CASCADE
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


def get_pilot_by_id(pilot_id):
    return get_db().execute(
        """
        SELECT
            pilots.id AS pilot_id,
            pilots.rank,
            users.id AS user_id,
            users.full_name,
            users.username
        FROM pilots
        JOIN users ON users.id = pilots.user_id
        WHERE pilots.id = ?
        """,
        (pilot_id,),
    ).fetchone()


def list_pilots():
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
        WHERE users.role = 'pilot'
        ORDER BY users.full_name
        """
    ).fetchall()


def update_pilot(pilot_id, full_name, username, rank):
    db = get_db()
    pilot = get_pilot_by_id(pilot_id)
    if pilot is None:
        return False

    try:
        db.execute(
            """
            UPDATE users
            SET full_name = ?, username = ?
            WHERE id = ? AND role = 'pilot'
            """,
            (full_name, username, pilot["user_id"]),
        )
        db.execute(
            """
            UPDATE pilots
            SET rank = ?
            WHERE id = ?
            """,
            (rank, pilot_id),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
        return False


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


def get_route_by_id(route_id, user_id):
    return get_db().execute(
        """
        SELECT id, user_id, departure_airport_id, destination_airport_id,
               estimated_duration_minutes, created_at
        FROM routes
        WHERE id = ? AND user_id = ?
        """,
        (route_id, user_id),
    ).fetchone()


def find_schedule_conflict(
    user_id,
    pilot_id,
    aircraft_id,
    departure_time,
    arrival_time,
    exclude_flight_id=None,
):
    db = get_db()
    params = (
        user_id,
        pilot_id,
        arrival_time,
        departure_time,
        exclude_flight_id,
        exclude_flight_id,
    )
    pilot_conflict = db.execute(
        """
        SELECT flight_number, departure_time, arrival_time
        FROM flights
        WHERE user_id = ?
            AND pilot_id = ?
            AND status != 'cancelled'
            AND departure_time < ?
            AND arrival_time > ?
            AND (? IS NULL OR id != ?)
        ORDER BY departure_time
        LIMIT 1
        """,
        params,
    ).fetchone()
    if pilot_conflict is not None:
        return {
            "type": "pilot",
            "flight_number": pilot_conflict["flight_number"],
            "departure_time": pilot_conflict["departure_time"],
            "arrival_time": pilot_conflict["arrival_time"],
        }

    params = (
        user_id,
        aircraft_id,
        arrival_time,
        departure_time,
        exclude_flight_id,
        exclude_flight_id,
    )
    aircraft_conflict = db.execute(
        """
        SELECT flight_number, departure_time, arrival_time
        FROM flights
        WHERE user_id = ?
            AND aircraft_id = ?
            AND status != 'cancelled'
            AND departure_time < ?
            AND arrival_time > ?
            AND (? IS NULL OR id != ?)
        ORDER BY departure_time
        LIMIT 1
        """,
        params,
    ).fetchone()
    if aircraft_conflict is not None:
        return {
            "type": "aircraft",
            "flight_number": aircraft_conflict["flight_number"],
            "departure_time": aircraft_conflict["departure_time"],
            "arrival_time": aircraft_conflict["arrival_time"],
        }

    return None


def create_flight(
    user_id,
    flight_number,
    route_id,
    pilot_id,
    aircraft_id,
    departure_time,
    arrival_time,
    status="scheduled",
):
    db = get_db()

    route = get_route_by_id(route_id, user_id)
    aircraft = get_aircraft_by_id(aircraft_id, user_id)
    pilot = get_pilot_by_id(pilot_id)
    if route is None or aircraft is None or pilot is None:
        return None

    if status != "cancelled" and find_schedule_conflict(
        user_id, pilot_id, aircraft_id, departure_time, arrival_time
    ):
        return None

    try:
        cursor = db.execute(
            """
            INSERT INTO flights (
                user_id,
                flight_number,
                route_id,
                pilot_id,
                aircraft_id,
                departure_time,
                arrival_time,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                flight_number.upper(),
                route_id,
                pilot_id,
                aircraft_id,
                departure_time,
                arrival_time,
                status,
            ),
        )
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        db.rollback()
        return None


def list_flights(user_id):
    return get_db().execute(
        """
        SELECT
            flights.id,
            flights.flight_number,
            flights.route_id,
            flights.pilot_id,
            flights.aircraft_id,
            flights.departure_time,
            flights.arrival_time,
            flights.status,
            pilot_user.full_name AS pilot_name,
            pilots.rank AS pilot_rank,
            aircrafts.name AS aircraft_name,
            aircrafts.model AS aircraft_model,
            departure.city AS departure_city,
            departure.iata_code AS departure_iata,
            destination.city AS destination_city,
            destination.iata_code AS destination_iata,
            COALESCE(GROUP_CONCAT(cabin_crews.full_name, ', '), '') AS cabin_crew_names
        FROM flights
        JOIN pilots ON pilots.id = flights.pilot_id
        JOIN users AS pilot_user ON pilot_user.id = pilots.user_id
        JOIN aircrafts ON aircrafts.id = flights.aircraft_id
        JOIN routes ON routes.id = flights.route_id
        JOIN airports AS departure ON departure.id = routes.departure_airport_id
        JOIN airports AS destination ON destination.id = routes.destination_airport_id
        LEFT JOIN flight_cabin_crews ON flight_cabin_crews.flight_id = flights.id
        LEFT JOIN cabin_crews ON cabin_crews.id = flight_cabin_crews.cabin_crew_id
        WHERE flights.user_id = ?
        GROUP BY flights.id
        ORDER BY flights.departure_time
        """,
        (user_id,),
    ).fetchall()


def create_cabin_crew(user_id, full_name, duty, phone=None):
    db = get_db()

    try:
        cursor = db.execute(
            """
            INSERT INTO cabin_crews (user_id, full_name, duty, phone)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, full_name, duty, phone),
        )
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        db.rollback()
        return None


def get_cabin_crew_by_id(cabin_crew_id, user_id):
    return get_db().execute(
        """
        SELECT id, user_id, full_name, duty, phone, is_active, created_at
        FROM cabin_crews
        WHERE id = ? AND user_id = ?
        """,
        (cabin_crew_id, user_id),
    ).fetchone()


def list_cabin_crews(user_id):
    return get_db().execute(
        """
        SELECT id, full_name, duty, phone, is_active, created_at
        FROM cabin_crews
        WHERE user_id = ?
        ORDER BY full_name
        """,
        (user_id,),
    ).fetchall()


def get_flight_by_id(flight_id, user_id):
    return get_db().execute(
        """
        SELECT id, user_id, flight_number, route_id, pilot_id, aircraft_id,
               departure_time, arrival_time, status, created_at
        FROM flights
        WHERE id = ? AND user_id = ?
        """,
        (flight_id, user_id),
    ).fetchone()


def update_flight(
    user_id,
    flight_id,
    flight_number,
    route_id,
    pilot_id,
    aircraft_id,
    departure_time,
    arrival_time,
    status,
):
    db = get_db()
    flight = get_flight_by_id(flight_id, user_id)
    route = get_route_by_id(route_id, user_id)
    aircraft = get_aircraft_by_id(aircraft_id, user_id)
    pilot = get_pilot_by_id(pilot_id)
    if flight is None or route is None or aircraft is None or pilot is None:
        return False

    if status != "cancelled" and find_schedule_conflict(
        user_id, pilot_id, aircraft_id, departure_time, arrival_time, flight_id
    ):
        return False

    try:
        db.execute(
            """
            UPDATE flights
            SET flight_number = ?,
                route_id = ?,
                pilot_id = ?,
                aircraft_id = ?,
                departure_time = ?,
                arrival_time = ?,
                status = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                flight_number.upper(),
                route_id,
                pilot_id,
                aircraft_id,
                departure_time,
                arrival_time,
                status,
                flight_id,
                user_id,
            ),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
        return False


def cancel_flight(user_id, flight_id):
    db = get_db()
    flight = get_flight_by_id(flight_id, user_id)
    if flight is None:
        return False

    try:
        db.execute(
            """
            UPDATE flights
            SET status = 'cancelled'
            WHERE id = ? AND user_id = ?
            """,
            (flight_id, user_id),
        )
        db.commit()
        return True
    except sqlite3.Error:
        db.rollback()
        return False


def assign_cabin_crew_to_flight(user_id, flight_id, cabin_crew_id):
    db = get_db()
    flight = get_flight_by_id(flight_id, user_id)
    cabin_crew = get_cabin_crew_by_id(cabin_crew_id, user_id)
    if flight is None or cabin_crew is None:
        return False

    try:
        db.execute(
            """
            INSERT INTO flight_cabin_crews (flight_id, cabin_crew_id)
            VALUES (?, ?)
            """,
            (flight_id, cabin_crew_id),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
        return False


def list_cabin_crews_for_flight(user_id, flight_id):
    flight = get_flight_by_id(flight_id, user_id)
    if flight is None:
        return []

    return get_db().execute(
        """
        SELECT cabin_crews.id, cabin_crews.full_name, cabin_crews.duty, cabin_crews.phone
        FROM flight_cabin_crews
        JOIN cabin_crews ON cabin_crews.id = flight_cabin_crews.cabin_crew_id
        WHERE flight_cabin_crews.flight_id = ?
        ORDER BY cabin_crews.full_name
        """,
        (flight_id,),
    ).fetchall()


def get_admin_dashboard_stats(user_id):
    db = get_db()
    return {
        "aircraft_count": db.execute(
            "SELECT COUNT(*) AS count FROM aircrafts WHERE user_id = ?",
            (user_id,),
        ).fetchone()["count"],
        "pilot_count": db.execute(
            """
            SELECT COUNT(*) AS count
            FROM pilots
            JOIN users ON users.id = pilots.user_id
            WHERE users.role = 'pilot'
            """
        ).fetchone()["count"],
        "flight_count": db.execute(
            "SELECT COUNT(*) AS count FROM flights WHERE user_id = ?",
            (user_id,),
        ).fetchone()["count"],
        "route_count": db.execute(
            "SELECT COUNT(*) AS count FROM routes WHERE user_id = ?",
            (user_id,),
        ).fetchone()["count"],
    }


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
