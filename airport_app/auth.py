from flask import Blueprint, render_template, request


auth_bp = Blueprint("auth", __name__)


FORM_CONFIG = {
    "admin_login": {
        "title": "Yönetici Girişi",
        "description": "Uçuşları, pilotları ve uçak operasyonlarını yönetmek için giriş yapın.",
        "button": "Yönetici girişi yap",
        "fields": ("username", "password"),
    },
    "admin_register": {
        "title": "Yönetici Kayıt",
        "description": "Yeni yönetici hesabı oluşturun.",
        "button": "Yönetici hesabı oluştur",
        "fields": ("full_name", "username", "password"),
    },
    "pilot_login": {
        "title": "Pilot Girişi",
        "description": "Size atanan uçuş ve ekip bilgilerini görmek için giriş yapın.",
        "button": "Pilot girişi yap",
        "fields": ("username", "password"),
    },
    "pilot_register": {
        "title": "Pilot Kayıt",
        "description": "Yeni pilot hesabı oluşturun.",
        "button": "Pilot hesabı oluştur",
        "fields": ("full_name", "rank", "username", "password"),
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

    if request.method == "POST":
        missing_fields = [
            field for field in config["fields"] if not request.form.get(field, "").strip()
        ]

        if missing_fields:
            error = "Lütfen tüm alanları doldurun."
        else:
            error = "Veritabanı bağlantısı sonraki adımda eklenecek."

    return render_template("auth/form.html", config=config, error=error)
