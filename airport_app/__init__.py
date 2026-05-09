from flask import Flask

from .admin import admin_bp
from .auth import auth_bp


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = "dev-secret-key-change-later"

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app
