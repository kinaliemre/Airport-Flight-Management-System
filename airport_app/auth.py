from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .db import create_user, get_user_for_login, verify_user_password


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
            user_id = create_user(
                full_name=form_data["full_name"],
                username=form_data["username"],
                password=form_data["password"],
                role=config["role"],
                rank=form_data.get("rank"),
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

    user = get_user_for_login(session["username"], "pilot")
    return render_template("pilot/dashboard.html", user=user)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Oturum kapatıldı.", "success")
    return redirect(url_for("auth.auth_home"))
