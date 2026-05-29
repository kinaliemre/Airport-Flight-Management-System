import os

from flask import Flask, session
from flask import render_template

from .admin import admin_bp
from .auth import auth_bp
from .db import DatabaseError, init_app as init_db_app
from .i18n import DEFAULT_LANGUAGE, normalize_language, translate_html


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
    register_i18n(app)

    return app


def handle_database_error(error):
    return render_template("errors/database.html", error=error), 500


def register_i18n(app):
    @app.context_processor
    def inject_language():
        language = normalize_language(session.get("language", DEFAULT_LANGUAGE))
        return {"current_lang": language}

    @app.after_request
    def translate_response(response):
        language = normalize_language(session.get("language", DEFAULT_LANGUAGE))
        if (
            language == "en"
            and response.status_code == 200
            and response.content_type
            and response.content_type.startswith("text/html")
        ):
            response.set_data(translate_html(response.get_data(as_text=True), language))
            response.headers["Content-Length"] = str(len(response.get_data()))
        return response
