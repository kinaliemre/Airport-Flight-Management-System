from flask import Blueprint, flash, redirect, render_template, session, url_for

from .db import list_aircrafts


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
def dashboard():
    if session.get("role") != "admin":
        flash("Yönetici paneline erişmek için giriş yapmalısınız.", "error")
        return redirect(url_for("auth.admin_login"))

    aircrafts = list_aircrafts(session["user_id"])
    return render_template("admin/dashboard.html", aircrafts=aircrafts)


@admin_bp.route("/old-login")
def login():
    return redirect(url_for("auth.admin_login"))
