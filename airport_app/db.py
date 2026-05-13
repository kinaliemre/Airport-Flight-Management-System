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
