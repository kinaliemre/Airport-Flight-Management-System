from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .db import (
    create_admin,
    create_cancellation_request,
    create_pilot,
    get_pilot_by_user_id,
    get_user_for_login,
    list_cancellation_requests_for_pilot,
    list_flights_for_pilot,
    verify_user_password,
)


auth_bp = Blueprint("auth", __name__)


FORM_CONFIG = {
    "admin_login": {
        "title": "Yönetici Girişi",
        "description": "Uçuşları, pilotları ve uçak operasyonlarını yönetmek için giriş yapın.",
        "button": "Yönetici girişi yap",
        "fields": ("username", "password"),
        "mode": "login",
        "role": "admin",
    },
    "admin_register": {
        "title": "Yönetici Kayıt",
        "description": "Yeni yönetici hesabı oluşturun.",
        "button": "Yönetici hesabı oluştur",
        "fields": ("full_name", "username", "password"),
        "mode": "register",
        "role": "admin",
    },
    "pilot_login": {
        "title": "Pilot Girişi",
        "description": "Size atanan uçuş ve ekip bilgilerini görmek için giriş yapın.",
        "button": "Pilot girişi yap",
        "fields": ("username", "password"),
        "mode": "login",
        "role": "pilot",
    },
    "pilot_register": {
        "title": "Pilot Kayıt",
        "description": "Yeni pilot hesabı oluşturun.",
        "button": "Pilot hesabı oluştur",
        "fields": ("full_name", "rank", "username", "password"),
        "mode": "register",
        "role": "pilot",
    },
}


@auth_bp.route("/")
def auth_home():
    return render_template("auth/home.html")


@auth_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    return render_auth_form("admin_login")


@auth_bp.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    return render_auth_form("admin_register")


@auth_bp.route("/pilot/login", methods=["GET", "POST"])
def pilot_login():
    return render_auth_form("pilot_login")


@auth_bp.route("/pilot/register", methods=["GET", "POST"])
def pilot_register():
    return render_auth_form("pilot_register")


def render_auth_form(form_type):
    config = FORM_CONFIG[form_type]
    error = None
    form_data = {}

    if request.method == "POST":
        form_data = {
            field: request.form.get(field, "").strip() for field in config["fields"]
        }
        missing_fields = [
            field for field in config["fields"] if not form_data.get(field)
        ]

        if missing_fields:
            error = "Lütfen tüm alanları doldurun."
        elif config["mode"] == "register":
            if config["role"] == "pilot":
                user_id = create_pilot(
                    full_name=form_data["full_name"],
                    username=form_data["username"],
                    password=form_data["password"],
                    rank=form_data["rank"],
                )
            else:
                user_id = create_admin(
                    full_name=form_data["full_name"],
                    username=form_data["username"],
                    password=form_data["password"],
                )

            if user_id is None:
                error = "Bu kullanıcı adı zaten kullanılıyor."
            else:
                flash("Kayıt başarılı. Şimdi giriş yapabilirsiniz.", "success")
                return redirect(url_for(f"auth.{config['role']}_login"))
        else:
            user = get_user_for_login(form_data["username"], config["role"])

            if not verify_user_password(user, form_data["password"]):
                error = "Kullanıcı adı veya şifre hatalı."
            else:
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["full_name"] = user["full_name"]
                session["role"] = user["role"]

                if user["role"] == "admin":
                    return redirect(url_for("admin.dashboard"))

                return redirect(url_for("auth.pilot_dashboard"))

    return render_template(
        "auth/form.html", config=config, error=error, form_data=form_data
    )


@auth_bp.route("/pilot/dashboard")
def pilot_dashboard():
    if session.get("role") != "pilot":
        flash("Pilot paneline erişmek için giriş yapmalısınız.", "error")
        return redirect(url_for("auth.pilot_login"))

    pilot = get_pilot_by_user_id(session["user_id"])
    flights = list_flights_for_pilot(pilot["pilot_id"]) if pilot else []
    cancellation_requests = (
        list_cancellation_requests_for_pilot(pilot["pilot_id"]) if pilot else []
    )
    request_by_flight = {
        request["flight_id"]: request for request in cancellation_requests
    }
    return render_template(
        "pilot/dashboard.html",
        user=pilot,
        flights=flights,
        request_by_flight=request_by_flight,
    )


@auth_bp.route("/pilot/flights/<int:flight_id>/cancellation-requests", methods=["POST"])
def create_pilot_cancellation_request(flight_id):
    if session.get("role") != "pilot":
        flash("Pilot paneline erişmek için giriş yapmalısınız.", "error")
        return redirect(url_for("auth.pilot_login"))

    pilot = get_pilot_by_user_id(session["user_id"])
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash("İptal talebi için sebep yazmalısınız.", "error")
        return redirect(url_for("auth.pilot_dashboard"))

    request_id, error = create_cancellation_request(
        pilot_id=pilot["pilot_id"],
        flight_id=flight_id,
        reason=reason,
    )

    if request_id is not None:
        flash("İptal talebiniz kaydedildi.", "success")
    elif error == "late":
        flash("Kalkışa 24 saatten az kaldığı için iptal talebi gönderilemez.", "error")
    else:
        flash("İptal talebi kaydedilemedi.", "error")

    return redirect(url_for("auth.pilot_dashboard"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Oturum kapatıldı.", "success")
    return redirect(url_for("auth.auth_home"))
