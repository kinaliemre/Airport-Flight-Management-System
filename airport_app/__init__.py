from flask import Flask

from .admin import admin_bp
from .auth import auth_bp
from .db import init_app as init_db_app


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = "dev-secret-key-change-later"
    app.config["DATABASE"] = app.instance_path + "/airport.sqlite"

    init_db_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app
