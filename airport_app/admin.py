from flask import Blueprint, flash, redirect, render_template, session, url_for

from .db import list_aircrafts, list_cabin_crews, list_flights, list_routes


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
def dashboard():
    if session.get("role") != "admin":
        flash("Yönetici paneline erişmek için giriş yapmalısınız.", "error")
        return redirect(url_for("auth.admin_login"))

    aircrafts = list_aircrafts(session["user_id"])
    cabin_crews = list_cabin_crews(session["user_id"])
    routes = list_routes(session["user_id"])
    flights = list_flights(session["user_id"])
    return render_template(
        "admin/dashboard.html",
        aircrafts=aircrafts,
        cabin_crews=cabin_crews,
        flights=flights,
        routes=routes,
    )


@admin_bp.route("/old-login")
def login():
    return redirect(url_for("auth.admin_login"))
