from flask import Blueprint, redirect, url_for


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
def dashboard():
    return redirect(url_for("auth.admin_login"))


@admin_bp.route("/old-login")
def login():
    return redirect(url_for("auth.admin_login"))
