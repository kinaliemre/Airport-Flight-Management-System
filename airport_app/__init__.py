import os

from flask import Flask
from flask import render_template

from .admin import admin_bp
from .auth import auth_bp
from .db import DatabaseError, init_app as init_db_app


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = "dev-secret-key-change-later"
    app.config["DATABASE"] = os.environ.get(
        "AIRPORT_DATABASE", os.path.join(app.instance_path, "airport.sqlite")
    )

    init_db_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_error_handler(DatabaseError, handle_database_error)

    return app


def handle_database_error(error):
    return render_template("errors/database.html", error=error), 500
