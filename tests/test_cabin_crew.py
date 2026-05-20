import os
import tempfile
import unittest

from airport_app import create_app
from airport_app.db import (
    create_admin,
    create_aircraft,
    create_airport,
    create_cabin_crew_account,
    create_flight,
    create_pilot,
    create_route,
    get_db,
    get_user_for_login,
)


class CabinCrewBusinessLogicTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        os.environ["AIRPORT_DATABASE"] = os.path.join(
            self.temp_dir.name, "test_airport.sqlite"
        )
        self.app = create_app()
        self.app.config.update(TESTING=True)

        with self.app.app_context():
            self.admin_id = create_admin("Admin User", "admin", "secret")
            pilot_user_id = create_pilot(
                "Pilot User", "pilot.user", "secret", "Captain"
            )
            self.pilot_id = get_db().execute(
                "SELECT id FROM pilots WHERE user_id = ?",
                (pilot_user_id,),
            ).fetchone()["id"]
            self.aircraft_id = create_aircraft(
                self.admin_id, "TC-CAB", "Airbus A320", 180, "30 rows"
            )
            departure_id = create_airport(
                self.admin_id, "Istanbul Airport", "Istanbul", "Turkiye", "IST"
            )
            destination_id = create_airport(
                self.admin_id, "Esenboga Airport", "Ankara", "Turkiye", "ESB"
            )
            self.route_id = create_route(
                self.admin_id, departure_id, destination_id, 65
            )
            self.cabin_crew_ids = [
                self._create_cabin_crew("Crew One", "crew.one"),
                self._create_cabin_crew("Crew Two", "crew.two"),
                self._create_cabin_crew("Crew Three", "crew.three"),
            ]

    def tearDown(self):
        os.environ.pop("AIRPORT_DATABASE", None)
        self.temp_dir.cleanup()

    def _create_cabin_crew(self, full_name, username):
        user_id = create_cabin_crew_account(
            self.admin_id, full_name, username, "secret", "Cabin Crew"
        )
        user = get_user_for_login(username, "cabin_crew")
        self.assertEqual(user["role"], "cabin_crew")
        return get_db().execute(
            "SELECT id FROM cabin_crews WHERE account_user_id = ?",
            (user_id,),
        ).fetchone()["id"]

    def test_flight_requires_three_cabin_crew_members(self):
        with self.app.app_context():
            rejected_flight_id = create_flight(
                self.admin_id,
                "TK3001",
                self.route_id,
                self.pilot_id,
                self.aircraft_id,
                "2026-06-01T10:00",
                "2026-06-01T12:00",
                cabin_crew_ids=self.cabin_crew_ids[:2],
            )
            self.assertIsNone(rejected_flight_id)

            flight_id = create_flight(
                self.admin_id,
                "TK3002",
                self.route_id,
                self.pilot_id,
                self.aircraft_id,
                "2026-06-01T10:00",
                "2026-06-01T12:00",
                cabin_crew_ids=self.cabin_crew_ids,
            )
            self.assertIsNotNone(flight_id)

            assigned_count = get_db().execute(
                "SELECT COUNT(*) AS count FROM flight_cabin_crews WHERE flight_id = ?",
                (flight_id,),
            ).fetchone()["count"]
            self.assertEqual(assigned_count, 3)


if __name__ == "__main__":
    unittest.main()
