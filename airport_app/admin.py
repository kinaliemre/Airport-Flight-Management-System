from flask import Blueprint, flash, redirect, render_template, session, url_for


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
def dashboard():
    if session.get("role") != "admin":
        flash("Yönetici paneline erişmek için giriş yapmalısınız.", "error")
        return redirect(url_for("auth.admin_login"))

    return render_template("admin/dashboard.html")


@admin_bp.route("/old-login")
def login():
    return redirect(url_for("auth.admin_login"))
