import sqlite3
from click import command, echo
from datetime import datetime, timedelta
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
                role TEXT NOT NULL CHECK (role IN ('admin', 'pilot', 'cabin_crew')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS pilots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                owner_user_id INTEGER,
                rank TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (owner_user_id) REFERENCES users (id) ON DELETE CASCADE
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
                account_user_id INTEGER UNIQUE,
                full_name TEXT NOT NULL,
                duty TEXT NOT NULL,
                phone TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (account_user_id) REFERENCES users (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS flight_cabin_crews (
                flight_id INTEGER NOT NULL,
                cabin_crew_id INTEGER NOT NULL,
                PRIMARY KEY (flight_id, cabin_crew_id),
                FOREIGN KEY (flight_id) REFERENCES flights (id) ON DELETE CASCADE,
                FOREIGN KEY (cabin_crew_id) REFERENCES cabin_crews (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cabin_crew_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lead_cabin_crew_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (lead_cabin_crew_id) REFERENCES cabin_crews (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cabin_crew_group_members (
                group_id INTEGER NOT NULL,
                cabin_crew_id INTEGER NOT NULL,
                PRIMARY KEY (group_id, cabin_crew_id),
                FOREIGN KEY (group_id) REFERENCES cabin_crew_groups (id) ON DELETE CASCADE,
                FOREIGN KEY (cabin_crew_id) REFERENCES cabin_crews (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cancellation_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                flight_id INTEGER NOT NULL,
                pilot_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                reviewed_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (flight_id) REFERENCES flights (id) ON DELETE CASCADE,
                FOREIGN KEY (pilot_id) REFERENCES pilots (id) ON DELETE CASCADE,
                FOREIGN KEY (reviewed_by) REFERENCES users (id) ON DELETE SET NULL
            );
            """
        )
        db.commit()
        ensure_schema_updates(db)
    except sqlite3.Error as error:
        db = g.get("db")
        if db is not None:
            db.rollback()
        raise DatabaseError("Veritabanı tabloları oluşturulamadı.") from error


def ensure_schema_updates(db):
    users_table = db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
    ).fetchone()
    if users_table is not None and "'cabin_crew'" not in users_table["sql"]:
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute(
            """
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'pilot', 'cabin_crew')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.execute(
            """
            INSERT INTO users_new (id, full_name, username, password_hash, role, created_at)
            SELECT id, full_name, username, password_hash, role, created_at
            FROM users
            """
        )
        db.execute("DROP TABLE users")
        db.execute("ALTER TABLE users_new RENAME TO users")
        db.execute("PRAGMA foreign_keys = ON")
        db.commit()

    pilot_columns = {
        row["name"] for row in db.execute("PRAGMA table_info(pilots)").fetchall()
    }
    if "owner_user_id" not in pilot_columns:
        db.execute("ALTER TABLE pilots ADD COLUMN owner_user_id INTEGER")
        db.commit()

    cabin_crew_columns = {
        row["name"] for row in db.execute("PRAGMA table_info(cabin_crews)").fetchall()
    }
    if "account_user_id" not in cabin_crew_columns:
        db.execute("ALTER TABLE cabin_crews ADD COLUMN account_user_id INTEGER")
        db.commit()
    db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cabin_crews_account_user_id
        ON cabin_crews (account_user_id)
        WHERE account_user_id IS NOT NULL
        """
    )
    db.commit()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS cabin_crew_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lead_cabin_crew_id INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (lead_cabin_crew_id) REFERENCES cabin_crews (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS cabin_crew_group_members (
            group_id INTEGER NOT NULL,
            cabin_crew_id INTEGER NOT NULL,
            PRIMARY KEY (group_id, cabin_crew_id),
            FOREIGN KEY (group_id) REFERENCES cabin_crew_groups (id) ON DELETE CASCADE,
            FOREIGN KEY (cabin_crew_id) REFERENCES cabin_crews (id) ON DELETE CASCADE
        );
        """
    )
    db.commit()


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


def create_user(full_name, username, password, role, rank=None, owner_user_id=None):
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
                "INSERT INTO pilots (user_id, owner_user_id, rank) VALUES (?, ?, ?)",
                (cursor.lastrowid, owner_user_id, rank),
            )

        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        db.rollback()
        return None


def create_admin(full_name, username, password):
    return create_user(full_name, username, password, role="admin")


def create_pilot(full_name, username, password, rank, owner_user_id=None):
    return create_user(
        full_name,
        username,
        password,
        role="pilot",
        rank=rank,
        owner_user_id=owner_user_id,
    )


def create_cabin_crew_account(
    owner_user_id, full_name, username, password, duty, phone=None
):
    db = get_db()

    try:
        cursor = db.execute(
            """
            INSERT INTO users (full_name, username, password_hash, role)
            VALUES (?, ?, ?, 'cabin_crew')
            """,
            (full_name, username, generate_password_hash(password)),
        )
        db.execute(
            """
            INSERT INTO cabin_crews (user_id, account_user_id, full_name, duty, phone)
            VALUES (?, ?, ?, ?, ?)
            """,
            (owner_user_id, cursor.lastrowid, full_name, duty, phone),
        )
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        db.rollback()
        return None


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


def list_pilots(owner_user_id=None):
    params = ()
    owner_filter = ""
    if owner_user_id is not None:
        owner_filter = "AND (pilots.owner_user_id = ? OR pilots.owner_user_id IS NULL)"
        params = (owner_user_id,)

    return get_db().execute(
        f"""
        SELECT
            pilots.id AS pilot_id,
            pilots.rank,
            pilots.owner_user_id,
            users.id AS user_id,
            users.full_name,
            users.username,
            users.created_at
        FROM pilots
        JOIN users ON users.id = pilots.user_id
        WHERE users.role = 'pilot'
            {owner_filter}
        ORDER BY users.full_name
        """,
        params,
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


def update_aircraft(user_id, aircraft_id, name, model, capacity, seat_info):
    db = get_db()
    if get_aircraft_by_id(aircraft_id, user_id) is None:
        return False

    try:
        db.execute(
            """
            UPDATE aircrafts
            SET name = ?, model = ?, capacity = ?, seat_info = ?
            WHERE id = ? AND user_id = ?
            """,
            (name, model, capacity, seat_info, aircraft_id, user_id),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
        return False


def delete_aircraft(user_id, aircraft_id):
    db = get_db()
    if get_aircraft_by_id(aircraft_id, user_id) is None:
        return False

    try:
        db.execute(
            "DELETE FROM aircrafts WHERE id = ? AND user_id = ?",
            (aircraft_id, user_id),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
        return False


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


def update_airport(user_id, airport_id, name, city, country, iata_code):
    db = get_db()
    if get_airport_by_id(airport_id, user_id) is None:
        return False

    try:
        db.execute(
            """
            UPDATE airports
            SET name = ?, city = ?, country = ?, iata_code = ?
            WHERE id = ? AND user_id = ?
            """,
            (name, city, country, iata_code.upper(), airport_id, user_id),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
        return False


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
            routes.departure_airport_id,
            routes.destination_airport_id,
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


def update_route(
    user_id, route_id, departure_airport_id, destination_airport_id, estimated_duration_minutes
):
    db = get_db()
    route = get_route_by_id(route_id, user_id)
    departure = get_airport_by_id(departure_airport_id, user_id)
    destination = get_airport_by_id(destination_airport_id, user_id)
    if route is None or departure is None or destination is None:
        return False

    try:
        db.execute(
            """
            UPDATE routes
            SET departure_airport_id = ?,
                destination_airport_id = ?,
                estimated_duration_minutes = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                departure_airport_id,
                destination_airport_id,
                estimated_duration_minutes,
                route_id,
                user_id,
            ),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
        return False


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


def find_cabin_crew_schedule_conflict(
    user_id,
    cabin_crew_ids,
    departure_time,
    arrival_time,
    exclude_flight_id=None,
):
    if not cabin_crew_ids:
        return None

    placeholders = ",".join("?" for _ in cabin_crew_ids)
    params = (
        user_id,
        arrival_time,
        departure_time,
        exclude_flight_id,
        exclude_flight_id,
        *cabin_crew_ids,
    )
    return get_db().execute(
        f"""
        SELECT flights.flight_number, flights.departure_time, flights.arrival_time,
               cabin_crews.full_name
        FROM flights
        JOIN flight_cabin_crews ON flight_cabin_crews.flight_id = flights.id
        JOIN cabin_crews ON cabin_crews.id = flight_cabin_crews.cabin_crew_id
        WHERE flights.user_id = ?
            AND flights.status != 'cancelled'
            AND flights.departure_time < ?
            AND flights.arrival_time > ?
            AND (? IS NULL OR flights.id != ?)
            AND flight_cabin_crews.cabin_crew_id IN ({placeholders})
        ORDER BY flights.departure_time
        LIMIT 1
        """,
        params,
    ).fetchone()


def replace_flight_cabin_crew_group(db, user_id, flight_id, cabin_crew_ids):
    if len(cabin_crew_ids) != 3 or len(set(cabin_crew_ids)) != 3:
        return False

    placeholders = ",".join("?" for _ in cabin_crew_ids)
    valid_count = db.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM cabin_crews
        WHERE user_id = ? AND is_active = 1 AND id IN ({placeholders})
        """,
        (user_id, *cabin_crew_ids),
    ).fetchone()["count"]
    if valid_count != 3:
        return False

    db.execute("DELETE FROM flight_cabin_crews WHERE flight_id = ?", (flight_id,))
    db.executemany(
        """
        INSERT INTO flight_cabin_crews (flight_id, cabin_crew_id)
        VALUES (?, ?)
        """,
        [(flight_id, cabin_crew_id) for cabin_crew_id in cabin_crew_ids],
    )
    return True


def create_flight(
    user_id,
    flight_number,
    route_id,
    pilot_id,
    aircraft_id,
    departure_time,
    arrival_time,
    status="scheduled",
    cabin_crew_ids=None,
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

    if cabin_crew_ids is not None:
        if len(cabin_crew_ids) != 3 or len(set(cabin_crew_ids)) != 3:
            return None
        if status != "cancelled" and find_cabin_crew_schedule_conflict(
            user_id, cabin_crew_ids, departure_time, arrival_time
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
        if cabin_crew_ids is not None and not replace_flight_cabin_crew_group(
            db, user_id, cursor.lastrowid, cabin_crew_ids
        ):
            db.rollback()
            return None
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        db.rollback()
        return None


def list_flights(user_id, include_cancelled=True):
    status_filter = "" if include_cancelled else "AND flights.status != 'cancelled'"
    return get_db().execute(
        f"""
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
            COALESCE(GROUP_CONCAT(cabin_crews.full_name, ', '), '') AS cabin_crew_names,
            COALESCE(GROUP_CONCAT(cabin_crews.id, ','), '') AS cabin_crew_ids
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
            {status_filter}
        GROUP BY flights.id
        ORDER BY flights.departure_time
        """,
        (user_id,),
    ).fetchall()


def list_cancelled_flights(user_id):
    return get_db().execute(
        """
        SELECT
            flights.id,
            flights.flight_number,
            flights.departure_time,
            flights.arrival_time,
            pilot_user.full_name AS pilot_name,
            aircrafts.name AS aircraft_name,
            aircrafts.model AS aircraft_model,
            departure.city AS departure_city,
            departure.iata_code AS departure_iata,
            destination.city AS destination_city,
            destination.iata_code AS destination_iata
        FROM flights
        JOIN pilots ON pilots.id = flights.pilot_id
        JOIN users AS pilot_user ON pilot_user.id = pilots.user_id
        JOIN aircrafts ON aircrafts.id = flights.aircraft_id
        JOIN routes ON routes.id = flights.route_id
        JOIN airports AS departure ON departure.id = routes.departure_airport_id
        JOIN airports AS destination ON destination.id = routes.destination_airport_id
        WHERE flights.user_id = ?
            AND flights.status = 'cancelled'
        ORDER BY flights.departure_time DESC
        """,
        (user_id,),
    ).fetchall()


def list_flights_for_pilot(pilot_id):
    return get_db().execute(
        """
        SELECT
            flights.id,
            flights.flight_number,
            flights.departure_time,
            flights.arrival_time,
            flights.status,
            aircrafts.name AS aircraft_name,
            aircrafts.model AS aircraft_model,
            aircrafts.capacity AS aircraft_capacity,
            aircrafts.seat_info AS aircraft_seat_info,
            departure.name AS departure_airport,
            departure.city AS departure_city,
            departure.country AS departure_country,
            departure.iata_code AS departure_iata,
            destination.name AS destination_airport,
            destination.city AS destination_city,
            destination.country AS destination_country,
            destination.iata_code AS destination_iata,
            routes.estimated_duration_minutes
        FROM flights
        JOIN aircrafts ON aircrafts.id = flights.aircraft_id
        JOIN routes ON routes.id = flights.route_id
        JOIN airports AS departure ON departure.id = routes.departure_airport_id
        JOIN airports AS destination ON destination.id = routes.destination_airport_id
        WHERE flights.pilot_id = ?
        ORDER BY flights.departure_time
        """,
        (pilot_id,),
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


def create_cabin_crew_group(user_id, members, lead_index):
    if len(members) != 3 or lead_index not in {0, 1, 2}:
        return None

    db = get_db()
    try:
        cabin_crew_ids = []
        for member in members:
            cursor = db.execute(
                """
                INSERT INTO cabin_crews (user_id, full_name, duty, phone)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    member["full_name"],
                    member["duty"],
                    member.get("phone"),
                ),
            )
            cabin_crew_ids.append(cursor.lastrowid)

        group_cursor = db.execute(
            """
            INSERT INTO cabin_crew_groups (user_id, lead_cabin_crew_id)
            VALUES (?, ?)
            """,
            (user_id, cabin_crew_ids[lead_index]),
        )
        group_id = group_cursor.lastrowid
        db.executemany(
            """
            INSERT INTO cabin_crew_group_members (group_id, cabin_crew_id)
            VALUES (?, ?)
            """,
            [(group_id, cabin_crew_id) for cabin_crew_id in cabin_crew_ids],
        )
        db.commit()
        return group_id
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
        SELECT id, account_user_id, full_name, duty, phone, is_active, created_at
        FROM cabin_crews
        WHERE user_id = ?
        ORDER BY full_name
        """,
        (user_id,),
    ).fetchall()


def list_cabin_crew_groups(user_id):
    return get_db().execute(
        """
        SELECT
            cabin_crew_groups.id,
            cabin_crew_groups.lead_cabin_crew_id,
            lead.full_name AS lead_name,
            lead.duty AS lead_duty,
            GROUP_CONCAT(member.full_name || '|' || member.duty || '|' || COALESCE(member.phone, ''), ';;') AS members
        FROM cabin_crew_groups
        JOIN cabin_crews AS lead ON lead.id = cabin_crew_groups.lead_cabin_crew_id
        JOIN cabin_crew_group_members ON cabin_crew_group_members.group_id = cabin_crew_groups.id
        JOIN cabin_crews AS member ON member.id = cabin_crew_group_members.cabin_crew_id
        WHERE cabin_crew_groups.user_id = ?
        GROUP BY cabin_crew_groups.id
        ORDER BY lead.full_name
        """,
        (user_id,),
    ).fetchall()


def get_cabin_crew_group_member_ids(user_id, group_id):
    group = get_db().execute(
        """
        SELECT id
        FROM cabin_crew_groups
        WHERE id = ? AND user_id = ?
        """,
        (group_id, user_id),
    ).fetchone()
    if group is None:
        return []

    return [
        row["cabin_crew_id"]
        for row in get_db()
        .execute(
            """
            SELECT cabin_crew_id
            FROM cabin_crew_group_members
            WHERE group_id = ?
            ORDER BY cabin_crew_id
            """,
            (group_id,),
        )
        .fetchall()
    ]


def get_cabin_crew_by_user_id(user_id):
    return get_db().execute(
        """
        SELECT
            cabin_crews.id AS cabin_crew_id,
            cabin_crews.user_id AS owner_user_id,
            cabin_crews.duty,
            cabin_crews.phone,
            cabin_crews.is_active,
            users.id AS user_id,
            users.full_name,
            users.username,
            users.created_at
        FROM cabin_crews
        JOIN users ON users.id = cabin_crews.account_user_id
        WHERE cabin_crews.account_user_id = ?
        """,
        (user_id,),
    ).fetchone()


def list_flights_for_cabin_crew(cabin_crew_id):
    return get_db().execute(
        """
        SELECT
            flights.id,
            flights.flight_number,
            flights.departure_time,
            flights.arrival_time,
            flights.status,
            pilot_user.full_name AS pilot_name,
            aircrafts.name AS aircraft_name,
            aircrafts.model AS aircraft_model,
            aircrafts.capacity AS aircraft_capacity,
            departure.name AS departure_airport,
            departure.city AS departure_city,
            departure.country AS departure_country,
            departure.iata_code AS departure_iata,
            destination.name AS destination_airport,
            destination.city AS destination_city,
            destination.country AS destination_country,
            destination.iata_code AS destination_iata,
            routes.estimated_duration_minutes
        FROM flight_cabin_crews
        JOIN flights ON flights.id = flight_cabin_crews.flight_id
        JOIN pilots ON pilots.id = flights.pilot_id
        JOIN users AS pilot_user ON pilot_user.id = pilots.user_id
        JOIN aircrafts ON aircrafts.id = flights.aircraft_id
        JOIN routes ON routes.id = flights.route_id
        JOIN airports AS departure ON departure.id = routes.departure_airport_id
        JOIN airports AS destination ON destination.id = routes.destination_airport_id
        WHERE flight_cabin_crews.cabin_crew_id = ?
        ORDER BY flights.departure_time
        """,
        (cabin_crew_id,),
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


def get_flight_for_pilot(flight_id, pilot_id):
    return get_db().execute(
        """
        SELECT id, user_id, flight_number, pilot_id, departure_time, arrival_time, status
        FROM flights
        WHERE id = ? AND pilot_id = ?
        """,
        (flight_id, pilot_id),
    ).fetchone()


def is_cancellation_request_late(departure_time, now=None):
    try:
        departure_at = datetime.fromisoformat(departure_time)
    except ValueError:
        return True

    current_time = now or datetime.now()
    return departure_at - current_time < timedelta(hours=24)


def create_cancellation_request(pilot_id, flight_id, reason, now=None):
    db = get_db()
    flight = get_flight_for_pilot(flight_id, pilot_id)
    if flight is None:
        return None, "not_found"

    existing_request = db.execute(
        """
        SELECT id
        FROM cancellation_requests
        WHERE flight_id = ? AND pilot_id = ? AND status = 'pending'
        """,
        (flight_id, pilot_id),
    ).fetchone()
    if existing_request is not None:
        return existing_request["id"], None

    try:
        cursor = db.execute(
            """
            INSERT INTO cancellation_requests (user_id, flight_id, pilot_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            (flight["user_id"], flight_id, pilot_id, reason),
        )
        db.commit()
        return cursor.lastrowid, None
    except sqlite3.IntegrityError:
        db.rollback()
        return None, "invalid"


def list_cancellation_requests_for_pilot(pilot_id):
    return get_db().execute(
        """
        SELECT
            cancellation_requests.id,
            cancellation_requests.flight_id,
            cancellation_requests.reason,
            cancellation_requests.status,
            cancellation_requests.created_at,
            flights.flight_number
        FROM cancellation_requests
        JOIN flights ON flights.id = cancellation_requests.flight_id
        WHERE cancellation_requests.pilot_id = ?
        ORDER BY cancellation_requests.created_at DESC
        """,
        (pilot_id,),
    ).fetchall()


def list_cancellation_requests(user_id):
    return get_db().execute(
        """
        SELECT
            cancellation_requests.id,
            cancellation_requests.flight_id,
            cancellation_requests.pilot_id,
            cancellation_requests.reason,
            cancellation_requests.status,
            cancellation_requests.created_at,
            cancellation_requests.reviewed_at,
            cancellation_requests.reviewed_by,
            flights.flight_number,
            flights.departure_time,
            flights.arrival_time,
            flights.status AS flight_status,
            pilot_user.full_name AS pilot_name,
            pilots.rank AS pilot_rank,
            aircrafts.name AS aircraft_name,
            departure.iata_code AS departure_iata,
            destination.iata_code AS destination_iata
        FROM cancellation_requests
        JOIN flights ON flights.id = cancellation_requests.flight_id
        JOIN pilots ON pilots.id = cancellation_requests.pilot_id
        JOIN users AS pilot_user ON pilot_user.id = pilots.user_id
        JOIN aircrafts ON aircrafts.id = flights.aircraft_id
        JOIN routes ON routes.id = flights.route_id
        JOIN airports AS departure ON departure.id = routes.departure_airport_id
        JOIN airports AS destination ON destination.id = routes.destination_airport_id
        ORDER BY
            CASE cancellation_requests.status
                WHEN 'pending' THEN 0
                WHEN 'approved' THEN 1
                ELSE 2
            END,
            cancellation_requests.created_at DESC
        """,
    ).fetchall()


def review_cancellation_request(user_id, request_id, status, reviewed_by):
    if status not in {"approved", "rejected"}:
        return False

    db = get_db()
    request_row = db.execute(
        """
        SELECT cancellation_requests.id, cancellation_requests.flight_id, cancellation_requests.status,
               flights.user_id AS flight_owner_id
        FROM cancellation_requests
        JOIN flights ON flights.id = cancellation_requests.flight_id
        WHERE cancellation_requests.id = ?
        """,
        (request_id,),
    ).fetchone()
    if request_row is None or request_row["status"] != "pending":
        return False

    try:
        db.execute(
            """
            UPDATE cancellation_requests
            SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
            WHERE id = ?
            """,
            (status, reviewed_by, request_id),
        )

        if status == "approved":
            db.execute(
                """
                UPDATE flights
                SET status = 'cancelled'
                WHERE id = ?
                """,
                (request_row["flight_id"],),
            )

        db.commit()
        return True
    except sqlite3.Error:
        db.rollback()
        return False


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
    cabin_crew_ids=None,
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

    if cabin_crew_ids is not None:
        if len(cabin_crew_ids) != 3 or len(set(cabin_crew_ids)) != 3:
            return False
        if status != "cancelled" and find_cabin_crew_schedule_conflict(
            user_id, cabin_crew_ids, departure_time, arrival_time, flight_id
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
        if cabin_crew_ids is not None and not replace_flight_cabin_crew_group(
            db, user_id, flight_id, cabin_crew_ids
        ):
            db.rollback()
            return False
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
