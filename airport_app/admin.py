from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .db import (
    create_aircraft,
    create_pilot,
    get_admin_dashboard_stats,
    list_aircrafts,
    list_cabin_crews,
    list_flights,
    list_pilots,
    list_routes,
    update_pilot,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def require_admin():
    if session.get("role") != "admin":
        flash("Yönetici paneline erişmek için giriş yapmalısınız.", "error")
        return redirect(url_for("auth.admin_login"))

    return None


@admin_bp.route("/")
def dashboard():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    aircrafts = list_aircrafts(session["user_id"])
    cabin_crews = list_cabin_crews(session["user_id"])
    routes = list_routes(session["user_id"])
    flights = list_flights(session["user_id"])
    pilots = list_pilots()
    stats = get_admin_dashboard_stats(session["user_id"])
    return render_template(
        "admin/dashboard.html",
        aircrafts=aircrafts,
        cabin_crews=cabin_crews,
        flights=flights,
        pilots=pilots,
        routes=routes,
        stats=stats,
    )


@admin_bp.route("/aircrafts", methods=["POST"])
def add_aircraft():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    name = request.form.get("name", "").strip()
    model = request.form.get("model", "").strip()
    capacity_text = request.form.get("capacity", "").strip()
    seat_info = request.form.get("seat_info", "").strip()

    if not all((name, model, capacity_text, seat_info)):
        flash("Uçak eklemek için tüm alanları doldurun.", "error")
        return redirect(url_for("admin.dashboard"))

    try:
        capacity = int(capacity_text)
    except ValueError:
        flash("Kapasite sayısal bir değer olmalıdır.", "error")
        return redirect(url_for("admin.dashboard"))

    if capacity <= 0:
        flash("Kapasite 0'dan büyük olmalıdır.", "error")
        return redirect(url_for("admin.dashboard"))

    aircraft_id = create_aircraft(
        user_id=session["user_id"],
        name=name,
        model=model,
        capacity=capacity,
        seat_info=seat_info,
    )

    if aircraft_id is None:
        flash("Bu uçak adı zaten kayıtlı veya bilgiler geçersiz.", "error")
    else:
        flash("Uçak başarıyla eklendi.", "success")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/pilots", methods=["POST"])
def add_pilot():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    full_name = request.form.get("full_name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    rank = request.form.get("rank", "").strip()

    if not all((full_name, username, password, rank)):
        flash("Pilot eklemek için tüm alanları doldurun.", "error")
        return redirect(url_for("admin.dashboard"))

    pilot_id = create_pilot(
        full_name=full_name,
        username=username,
        password=password,
        rank=rank,
    )

    if pilot_id is None:
        flash("Bu kullanıcı adı zaten kayıtlı.", "error")
    else:
        flash("Pilot başarıyla eklendi.", "success")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/pilots/<int:pilot_id>", methods=["POST"])
def edit_pilot(pilot_id):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    full_name = request.form.get("full_name", "").strip()
    username = request.form.get("username", "").strip()
    rank = request.form.get("rank", "").strip()

    if not all((full_name, username, rank)):
        flash("Pilot bilgilerini güncellemek için tüm alanları doldurun.", "error")
        return redirect(url_for("admin.dashboard"))

    if update_pilot(
        pilot_id=pilot_id,
        full_name=full_name,
        username=username,
        rank=rank,
    ):
        flash("Pilot bilgileri güncellendi.", "success")
    else:
        flash("Pilot bulunamadı veya kullanıcı adı zaten kayıtlı.", "error")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/old-login")
def login():
    return redirect(url_for("auth.admin_login"))
