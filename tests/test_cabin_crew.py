import os
import tempfile
import unittest

from airport_app import create_app
from airport_app.db import (
    cancel_flight,
    create_admin,
    create_aircraft,
    create_airport,
    create_cabin_crew_account,
    create_cancellation_request,
    create_flight,
    create_pilot,
    create_route,
    get_db,
    get_user_for_login,
    list_cancelled_flights,
    list_cancellation_requests,
    list_flights,
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

    def test_admin_sees_pilot_cancellation_request_and_cancelled_flight_is_separate(self):
        with self.app.app_context():
            flight_id = create_flight(
                self.admin_id,
                "TK3003",
                self.route_id,
                self.pilot_id,
                self.aircraft_id,
                "2026-05-01T10:00",
                "2026-05-01T12:00",
                cabin_crew_ids=self.cabin_crew_ids,
            )
            self.assertIsNotNone(flight_id)

            request_id, error = create_cancellation_request(
                self.pilot_id, flight_id, "Test cancellation"
            )
            self.assertIsNotNone(request_id)
            self.assertIsNone(error)

            admin_requests = list_cancellation_requests(self.admin_id)
            self.assertEqual(len(admin_requests), 1)
            self.assertEqual(admin_requests[0]["reason"], "Test cancellation")

            self.assertTrue(cancel_flight(self.admin_id, flight_id))
            active_flights = list_flights(self.admin_id, include_cancelled=False)
            cancelled_flights = list_cancelled_flights(self.admin_id)
            self.assertEqual(len(active_flights), 0)
            self.assertEqual(len(cancelled_flights), 1)
            self.assertEqual(cancelled_flights[0]["flight_number"], "TK3003")

    def test_admin_sees_cancellation_request_by_flight_owner_even_if_request_user_differs(self):
        with self.app.app_context():
            flight_id = create_flight(
                self.admin_id,
                "TK3004",
                self.route_id,
                self.pilot_id,
                self.aircraft_id,
                "2026-05-02T10:00",
                "2026-05-02T12:00",
                cabin_crew_ids=self.cabin_crew_ids,
            )
            self.assertIsNotNone(flight_id)

            other_admin_id = create_admin("Other Admin", "other.admin", "secret")
            get_db().execute(
                """
                INSERT INTO cancellation_requests (user_id, flight_id, pilot_id, reason)
                VALUES (?, ?, ?, ?)
                """,
                (other_admin_id, flight_id, self.pilot_id, "Owner-based visibility"),
            )
            get_db().commit()

            admin_requests = list_cancellation_requests(self.admin_id)
            self.assertEqual(len(admin_requests), 1)
            self.assertEqual(admin_requests[0]["reason"], "Owner-based visibility")


if __name__ == "__main__":
    unittest.main()
