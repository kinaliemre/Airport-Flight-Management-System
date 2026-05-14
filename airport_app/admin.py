from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .db import (
    cancel_flight,
    create_aircraft,
    create_flight,
    create_pilot,
    find_schedule_conflict,
    get_admin_dashboard_stats,
    list_aircrafts,
    list_cabin_crews,
    list_flights,
    list_pilots,
    list_routes,
    update_flight,
    update_pilot,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

FLIGHT_STATUSES = {"scheduled", "delayed", "cancelled", "completed"}


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


def read_flight_form():
    form_data = {
        "flight_number": request.form.get("flight_number", "").strip(),
        "route_id": request.form.get("route_id", "").strip(),
        "pilot_id": request.form.get("pilot_id", "").strip(),
        "aircraft_id": request.form.get("aircraft_id", "").strip(),
        "departure_time": request.form.get("departure_time", "").strip(),
        "arrival_time": request.form.get("arrival_time", "").strip(),
        "status": request.form.get("status", "scheduled").strip(),
    }

    if not all(form_data.values()):
        return None, "Uçuş bilgileri için tüm alanları doldurun."

    try:
        form_data["route_id"] = int(form_data["route_id"])
        form_data["pilot_id"] = int(form_data["pilot_id"])
        form_data["aircraft_id"] = int(form_data["aircraft_id"])
    except ValueError:
        return None, "Uçuş için rota, pilot ve uçak seçimi geçersiz."

    if form_data["departure_time"] >= form_data["arrival_time"]:
        return None, "Varış zamanı kalkış zamanından sonra olmalıdır."

    if form_data["status"] not in FLIGHT_STATUSES:
        return None, "Uçuş durumu geçersiz."

    return form_data, None


def get_schedule_conflict_error(form_data, flight_id=None):
    if form_data["status"] == "cancelled":
        return None

    conflict = find_schedule_conflict(
        user_id=session["user_id"],
        pilot_id=form_data["pilot_id"],
        aircraft_id=form_data["aircraft_id"],
        departure_time=form_data["departure_time"],
        arrival_time=form_data["arrival_time"],
        exclude_flight_id=flight_id,
    )
    if conflict is None:
        return None

    resource_label = "Pilot" if conflict["type"] == "pilot" else "Uçak"
    return (
        f"{resource_label} çakışması: {conflict['flight_number']} "
        f"({conflict['departure_time']} - {conflict['arrival_time']})"
    )


@admin_bp.route("/flights", methods=["POST"])
def add_flight():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    form_data, error = read_flight_form()
    if error is not None:
        flash(error, "error")
        return redirect(url_for("admin.dashboard"))

    conflict_error = get_schedule_conflict_error(form_data)
    if conflict_error is not None:
        flash(conflict_error, "error")
        return redirect(url_for("admin.dashboard"))

    flight_id = create_flight(user_id=session["user_id"], **form_data)

    if flight_id is None:
        flash("Uçuş oluşturulamadı. Uçuş numarası veya seçimler geçersiz olabilir.", "error")
    else:
        flash("Uçuş başarıyla oluşturuldu.", "success")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/flights/<int:flight_id>", methods=["POST"])
def edit_flight(flight_id):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    form_data, error = read_flight_form()
    if error is not None:
        flash(error, "error")
        return redirect(url_for("admin.dashboard"))

    conflict_error = get_schedule_conflict_error(form_data, flight_id)
    if conflict_error is not None:
        flash(conflict_error, "error")
        return redirect(url_for("admin.dashboard"))

    if update_flight(user_id=session["user_id"], flight_id=flight_id, **form_data):
        flash("Uçuş bilgileri güncellendi.", "success")
    else:
        flash("Uçuş güncellenemedi. Uçuş numarası veya seçimler geçersiz olabilir.", "error")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/flights/<int:flight_id>/cancel", methods=["POST"])
def cancel_flight_route(flight_id):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    if cancel_flight(session["user_id"], flight_id):
        flash("Uçuş iptal edildi.", "success")
    else:
        flash("Uçuş iptal edilemedi.", "error")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/old-login")
def login():
    return redirect(url_for("auth.admin_login"))
