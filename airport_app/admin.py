from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .db import (
    cancel_flight,
    create_aircraft,
    create_airport,
    create_cabin_crew_group,
    create_flight,
    create_pilot,
    create_route,
    delete_aircraft,
    find_cabin_crew_schedule_conflict,
    find_schedule_conflict,
    get_admin_dashboard_stats,
    get_cabin_crew_group_member_ids,
    list_aircrafts,
    list_airports,
    list_cabin_crew_groups,
    list_cabin_crews,
    list_cancellation_requests,
    list_flights,
    list_pilots,
    list_routes,
    review_cancellation_request,
    update_aircraft,
    update_airport,
    update_flight,
    update_pilot,
    update_route,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

FLIGHT_STATUSES = {"scheduled", "delayed", "cancelled", "completed"}
AIRPORT_OPTIONS = [
    {
        "code": "IST",
        "name": "Istanbul Airport",
        "city": "Istanbul",
        "country": "Turkiye",
    },
    {
        "code": "SAW",
        "name": "Sabiha Gokcen International Airport",
        "city": "Istanbul",
        "country": "Turkiye",
    },
    {
        "code": "ESB",
        "name": "Esenboga Airport",
        "city": "Ankara",
        "country": "Turkiye",
    },
    {
        "code": "ADB",
        "name": "Adnan Menderes Airport",
        "city": "Izmir",
        "country": "Turkiye",
    },
    {
        "code": "AYT",
        "name": "Antalya Airport",
        "city": "Antalya",
        "country": "Turkiye",
    },
    {
        "code": "DLM",
        "name": "Dalaman Airport",
        "city": "Mugla",
        "country": "Turkiye",
    },
    {
        "code": "BJV",
        "name": "Milas Bodrum Airport",
        "city": "Mugla",
        "country": "Turkiye",
    },
    {
        "code": "TZX",
        "name": "Trabzon Airport",
        "city": "Trabzon",
        "country": "Turkiye",
    },
    {
        "code": "ADA",
        "name": "Adana Sakirpasa Airport",
        "city": "Adana",
        "country": "Turkiye",
    },
    {
        "code": "GZT",
        "name": "Gaziantep Airport",
        "city": "Gaziantep",
        "country": "Turkiye",
    },
    {
        "code": "FRA",
        "name": "Frankfurt Airport",
        "city": "Frankfurt",
        "country": "Germany",
    },
    {
        "code": "MUC",
        "name": "Munich Airport",
        "city": "Munich",
        "country": "Germany",
    },
    {
        "code": "BER",
        "name": "Berlin Brandenburg Airport",
        "city": "Berlin",
        "country": "Germany",
    },
    {
        "code": "DUS",
        "name": "Dusseldorf Airport",
        "city": "Dusseldorf",
        "country": "Germany",
    },
    {
        "code": "HAM",
        "name": "Hamburg Airport",
        "city": "Hamburg",
        "country": "Germany",
    },
    {
        "code": "CGN",
        "name": "Cologne Bonn Airport",
        "city": "Cologne",
        "country": "Germany",
    },
    {
        "code": "CDG",
        "name": "Charles de Gaulle Airport",
        "city": "Paris",
        "country": "France",
    },
    {
        "code": "ORY",
        "name": "Paris Orly Airport",
        "city": "Paris",
        "country": "France",
    },
    {
        "code": "NCE",
        "name": "Nice Cote d'Azur Airport",
        "city": "Nice",
        "country": "France",
    },
    {
        "code": "LYS",
        "name": "Lyon Saint Exupery Airport",
        "city": "Lyon",
        "country": "France",
    },
    {
        "code": "MRS",
        "name": "Marseille Provence Airport",
        "city": "Marseille",
        "country": "France",
    },
    {
        "code": "TLS",
        "name": "Toulouse Blagnac Airport",
        "city": "Toulouse",
        "country": "France",
    },
    {
        "code": "MAD",
        "name": "Adolfo Suarez Madrid Barajas Airport",
        "city": "Madrid",
        "country": "Spain",
    },
    {
        "code": "BCN",
        "name": "Barcelona El Prat Airport",
        "city": "Barcelona",
        "country": "Spain",
    },
    {
        "code": "PMI",
        "name": "Palma de Mallorca Airport",
        "city": "Palma",
        "country": "Spain",
    },
    {
        "code": "AGP",
        "name": "Malaga Airport",
        "city": "Malaga",
        "country": "Spain",
    },
    {
        "code": "ALC",
        "name": "Alicante Elche Airport",
        "city": "Alicante",
        "country": "Spain",
    },
    {
        "code": "VLC",
        "name": "Valencia Airport",
        "city": "Valencia",
        "country": "Spain",
    },
    {
        "code": "SVO",
        "name": "Sheremetyevo International Airport",
        "city": "Moscow",
        "country": "Russia",
    },
    {
        "code": "DME",
        "name": "Domodedovo Airport",
        "city": "Moscow",
        "country": "Russia",
    },
    {
        "code": "VKO",
        "name": "Vnukovo International Airport",
        "city": "Moscow",
        "country": "Russia",
    },
    {
        "code": "LED",
        "name": "Pulkovo Airport",
        "city": "Saint Petersburg",
        "country": "Russia",
    },
    {
        "code": "AER",
        "name": "Sochi International Airport",
        "city": "Sochi",
        "country": "Russia",
    },
    {
        "code": "KZN",
        "name": "Kazan International Airport",
        "city": "Kazan",
        "country": "Russia",
    },
    {
        "code": "LHR",
        "name": "Heathrow Airport",
        "city": "London",
        "country": "United Kingdom",
    },
    {
        "code": "LGW",
        "name": "Gatwick Airport",
        "city": "London",
        "country": "United Kingdom",
    },
    {
        "code": "MAN",
        "name": "Manchester Airport",
        "city": "Manchester",
        "country": "United Kingdom",
    },
    {
        "code": "STN",
        "name": "Stansted Airport",
        "city": "London",
        "country": "United Kingdom",
    },
    {
        "code": "EDI",
        "name": "Edinburgh Airport",
        "city": "Edinburgh",
        "country": "United Kingdom",
    },
    {
        "code": "BHX",
        "name": "Birmingham Airport",
        "city": "Birmingham",
        "country": "United Kingdom",
    },
]
AIRPORT_OPTIONS_BY_CODE = {airport["code"]: airport for airport in AIRPORT_OPTIONS}


def require_admin():
    if session.get("role") != "admin":
        flash("Yönetici paneline erişmek için giriş yapmalısınız.", "error")
        return redirect(url_for("auth.admin_login"))

    return None


def parse_positive_int(value, field_name):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name} sayısal bir değer olmalıdır."

    if number <= 0:
        return None, f"{field_name} 0'dan büyük olmalıdır."

    return number, None


@admin_bp.route("/")
def dashboard():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    aircrafts = list_aircrafts(session["user_id"])
    airports = list_airports(session["user_id"])
    cabin_crews = list_cabin_crews(session["user_id"])
    cabin_crew_groups = list_cabin_crew_groups(session["user_id"])
    routes = list_routes(session["user_id"])
    flights = list_flights(session["user_id"])
    pilots = list_pilots(session["user_id"])
    cancellation_requests = list_cancellation_requests(session["user_id"])
    stats = get_admin_dashboard_stats(session["user_id"])
    return render_template(
        "admin/dashboard.html",
        aircrafts=aircrafts,
        airport_options=AIRPORT_OPTIONS,
        airports=airports,
        cabin_crew_groups=cabin_crew_groups,
        cabin_crews=cabin_crews,
        cancellation_requests=cancellation_requests,
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
    capacity, error = parse_positive_int(request.form.get("capacity", ""), "Kapasite")
    seat_info = request.form.get("seat_info", "").strip()

    if not all((name, model, seat_info)) or error is not None:
        flash(error or "Uçak eklemek için tüm alanları doldurun.", "error")
        return redirect(url_for("admin.dashboard"))

    aircraft_id = create_aircraft(session["user_id"], name, model, capacity, seat_info)
    if aircraft_id is None:
        flash("Bu uçak adı zaten kayıtlı veya bilgiler geçersiz.", "error")
    else:
        flash("Uçak başarıyla eklendi.", "success")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/aircrafts/<int:aircraft_id>", methods=["POST"])
def edit_aircraft(aircraft_id):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    name = request.form.get("name", "").strip()
    model = request.form.get("model", "").strip()
    capacity, error = parse_positive_int(request.form.get("capacity", ""), "Kapasite")
    seat_info = request.form.get("seat_info", "").strip()

    if not all((name, model, seat_info)) or error is not None:
        flash(error or "Uçak bilgilerini güncellemek için tüm alanları doldurun.", "error")
        return redirect(url_for("admin.dashboard"))

    if update_aircraft(session["user_id"], aircraft_id, name, model, capacity, seat_info):
        flash("Uçak bilgileri güncellendi.", "success")
    else:
        flash("Uçak güncellenemedi. İsim çakışması veya geçersiz bilgi olabilir.", "error")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/aircrafts/<int:aircraft_id>/delete", methods=["POST"])
def remove_aircraft(aircraft_id):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    if delete_aircraft(session["user_id"], aircraft_id):
        flash("Uçak silindi.", "success")
    else:
        flash("Uçak silinemedi. Bağlı uçuş kaydı olabilir.", "error")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/airports", methods=["POST"])
def add_airport():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    airport_code = request.form.get("airport_code", "").strip().upper()
    selected_airport = AIRPORT_OPTIONS_BY_CODE.get(airport_code)

    if selected_airport is None:
        flash("Listeden geçerli bir havalimanı seçin.", "error")
        return redirect(url_for("admin.dashboard"))

    airport_id = create_airport(
        session["user_id"],
        selected_airport["name"],
        selected_airport["city"],
        selected_airport["country"],
        selected_airport["code"],
    )
    if airport_id is None:
        flash("Bu IATA kodu zaten kayıtlı veya bilgiler geçersiz.", "error")
    else:
        flash("Havalimanı başarıyla eklendi.", "success")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/airports/<int:airport_id>", methods=["POST"])
def edit_airport(airport_id):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    name = request.form.get("name", "").strip()
    city = request.form.get("city", "").strip()
    country = request.form.get("country", "").strip()
    iata_code = request.form.get("iata_code", "").strip()

    if not all((name, city, country, iata_code)):
        flash("Havalimanı bilgilerini güncellemek için tüm alanları doldurun.", "error")
        return redirect(url_for("admin.dashboard"))

    if update_airport(session["user_id"], airport_id, name, city, country, iata_code):
        flash("Havalimanı bilgileri güncellendi.", "success")
    else:
        flash("Havalimanı güncellenemedi.", "error")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/routes", methods=["POST"])
def add_route():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    departure_id, departure_error = parse_positive_int(
        request.form.get("departure_airport_id"), "Kalkış havalimanı"
    )
    destination_id, destination_error = parse_positive_int(
        request.form.get("destination_airport_id"), "Varış havalimanı"
    )
    duration, duration_error = parse_positive_int(
        request.form.get("estimated_duration_minutes"), "Süre"
    )
    error = departure_error or destination_error or duration_error

    if error is not None:
        flash(error, "error")
        return redirect(url_for("admin.dashboard"))

    route_id = create_route(session["user_id"], departure_id, destination_id, duration)
    if route_id is None:
        flash("Rota oluşturulamadı. Havalimanları farklı olmalı ve rota tekrar etmemeli.", "error")
    else:
        flash("Rota başarıyla oluşturuldu.", "success")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/routes/<int:route_id>", methods=["POST"])
def edit_route(route_id):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    departure_id, departure_error = parse_positive_int(
        request.form.get("departure_airport_id"), "Kalkış havalimanı"
    )
    destination_id, destination_error = parse_positive_int(
        request.form.get("destination_airport_id"), "Varış havalimanı"
    )
    duration, duration_error = parse_positive_int(
        request.form.get("estimated_duration_minutes"), "Süre"
    )
    error = departure_error or destination_error or duration_error

    if error is not None:
        flash(error, "error")
        return redirect(url_for("admin.dashboard"))

    if update_route(session["user_id"], route_id, departure_id, destination_id, duration):
        flash("Rota bilgileri güncellendi.", "success")
    else:
        flash("Rota güncellenemedi.", "error")

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

    pilot_id = create_pilot(full_name, username, password, rank, session["user_id"])
    if pilot_id is None:
        flash("Bu kullanıcı adı zaten kayıtlı.", "error")
    else:
        flash("Pilot başarıyla eklendi.", "success")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/cabin-crews", methods=["POST"])
def add_cabin_crew():
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    members = []
    for index in range(1, 4):
        members.append(
            {
                "full_name": request.form.get(f"member_{index}_full_name", "").strip(),
                "duty": request.form.get(f"member_{index}_duty", "").strip(),
                "phone": request.form.get(f"member_{index}_phone", "").strip() or None,
            }
        )

    try:
        lead_index = int(request.form.get("lead_index", "1")) - 1
    except ValueError:
        lead_index = -1

    if any(not member["full_name"] or not member["duty"] for member in members):
        flash("Kabin gÃ¶revlisi eklemek iÃ§in zorunlu alanlarÄ± doldurun.", "error")
        return redirect(url_for("admin.dashboard"))

    group_id = create_cabin_crew_group(session["user_id"], members, lead_index)
    if group_id is None:
        flash("Bu kullanÄ±cÄ± adÄ± zaten kayÄ±tlÄ±.", "error")
    else:
        flash("Kabin gÃ¶revlisi baÅŸarÄ±yla eklendi.", "success")

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

    if update_pilot(pilot_id, full_name, username, rank):
        flash("Pilot bilgileri güncellendi.", "success")
    else:
        flash("Pilot bulunamadı veya kullanıcı adı zaten kayıtlı.", "error")

    return redirect(url_for("admin.dashboard"))


def read_flight_form(require_cabin_group=True):
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
        cabin_crew_group_id = request.form.get("cabin_crew_group_id", "").strip()
        if cabin_crew_group_id:
            form_data["cabin_crew_ids"] = get_cabin_crew_group_member_ids(
                session["user_id"], int(cabin_crew_group_id)
            )
        else:
            form_data["cabin_crew_ids"] = None
    except ValueError:
        return None, "Uçuş için rota, pilot ve uçak seçimi geçersiz."

    if require_cabin_group and (
        form_data["cabin_crew_ids"] is None or len(form_data["cabin_crew_ids"]) != 3
    ):
        return None, "Ucus icin 3 kisilik bir kabin ekibi secin."

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
        if not form_data.get("cabin_crew_ids"):
            return None

        cabin_crew_conflict = find_cabin_crew_schedule_conflict(
            user_id=session["user_id"],
            cabin_crew_ids=form_data["cabin_crew_ids"],
            departure_time=form_data["departure_time"],
            arrival_time=form_data["arrival_time"],
            exclude_flight_id=flight_id,
        )
        if cabin_crew_conflict is None:
            return None

        return (
            f"Kabin ekibi cakismasi: {cabin_crew_conflict['full_name']} "
            f"{cabin_crew_conflict['flight_number']} ucusunda "
            f"({cabin_crew_conflict['departure_time']} - "
            f"{cabin_crew_conflict['arrival_time']})"
        )

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

    form_data, error = read_flight_form(require_cabin_group=True)
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

    form_data, error = read_flight_form(require_cabin_group=False)
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


@admin_bp.route("/cancellation-requests/<int:request_id>/<action>", methods=["POST"])
def review_cancellation_request_route(request_id, action):
    auth_redirect = require_admin()
    if auth_redirect is not None:
        return auth_redirect

    status_by_action = {"approve": "approved", "reject": "rejected"}
    status = status_by_action.get(action)
    if status is None:
        flash("Geçersiz talep işlemi.", "error")
        return redirect(url_for("admin.dashboard"))

    if review_cancellation_request(
        user_id=session["user_id"],
        request_id=request_id,
        status=status,
        reviewed_by=session["user_id"],
    ):
        if status == "approved":
            flash("İptal talebi onaylandı ve uçuş iptal edildi.", "success")
        else:
            flash("İptal talebi reddedildi.", "success")
    else:
        flash("İptal talebi güncellenemedi.", "error")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/old-login")
def login():
    return redirect(url_for("auth.admin_login"))
