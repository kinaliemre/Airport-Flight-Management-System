import os
import tempfile
import unittest

from airport_app import create_app
from airport_app.db import (
    create_admin,
    create_aircraft,
    create_airport,
    create_flight,
    create_pilot,
    create_route,
    get_db,
    get_flight_by_id,
    update_flight,
)


class FlightConflictTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        os.environ["AIRPORT_DATABASE"] = os.path.join(
            self.temp_dir.name, "test_airport.sqlite"
        )
        self.app = create_app()
        self.app.config.update(TESTING=True)

        with self.app.app_context():
            self.admin_id = create_admin("Admin User", "admin", "secret")
            first_pilot_user_id = create_pilot(
                "First Pilot", "first.pilot", "secret", "Captain"
            )
            second_pilot_user_id = create_pilot(
                "Second Pilot", "second.pilot", "secret", "First Officer"
            )
            self.first_pilot_id = self._pilot_id_for_user(first_pilot_user_id)
            self.second_pilot_id = self._pilot_id_for_user(second_pilot_user_id)
            self.first_aircraft_id = create_aircraft(
                self.admin_id, "TC-ONE", "Airbus A320", 180, "30 rows"
            )
            self.second_aircraft_id = create_aircraft(
                self.admin_id, "TC-TWO", "Boeing 737", 160, "27 rows"
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

    def tearDown(self):
        os.environ.pop("AIRPORT_DATABASE", None)
        self.temp_dir.cleanup()

    def _pilot_id_for_user(self, user_id):
        return get_db().execute(
            "SELECT id FROM pilots WHERE user_id = ?",
            (user_id,),
        ).fetchone()["id"]

    def test_create_flight_blocks_pilot_and_aircraft_conflicts(self):
        with self.app.app_context():
            base_flight_id = create_flight(
                self.admin_id,
                "TK1001",
                self.route_id,
                self.first_pilot_id,
                self.first_aircraft_id,
                "2026-06-01T10:00",
                "2026-06-01T12:00",
            )
            self.assertIsNotNone(base_flight_id)

            pilot_conflict_id = create_flight(
                self.admin_id,
                "TK1002",
                self.route_id,
                self.first_pilot_id,
                self.second_aircraft_id,
                "2026-06-01T11:00",
                "2026-06-01T13:00",
            )
            self.assertIsNone(pilot_conflict_id)

            aircraft_conflict_id = create_flight(
                self.admin_id,
                "TK1003",
                self.route_id,
                self.second_pilot_id,
                self.first_aircraft_id,
                "2026-06-01T11:00",
                "2026-06-01T13:00",
            )
            self.assertIsNone(aircraft_conflict_id)

            adjacent_flight_id = create_flight(
                self.admin_id,
                "TK1004",
                self.route_id,
                self.first_pilot_id,
                self.first_aircraft_id,
                "2026-06-01T12:00",
                "2026-06-01T14:00",
            )
            self.assertIsNotNone(adjacent_flight_id)

    def test_update_flight_blocks_conflicts(self):
        with self.app.app_context():
            first_flight_id = create_flight(
                self.admin_id,
                "TK2001",
                self.route_id,
                self.first_pilot_id,
                self.first_aircraft_id,
                "2026-06-01T10:00",
                "2026-06-01T12:00",
            )
            second_flight_id = create_flight(
                self.admin_id,
                "TK2002",
                self.route_id,
                self.second_pilot_id,
                self.second_aircraft_id,
                "2026-06-01T13:00",
                "2026-06-01T15:00",
            )
            self.assertIsNotNone(first_flight_id)
            self.assertIsNotNone(second_flight_id)

            updated = update_flight(
                self.admin_id,
                second_flight_id,
                "TK2002",
                self.route_id,
                self.second_pilot_id,
                self.first_aircraft_id,
                "2026-06-01T11:00",
                "2026-06-01T14:00",
                "scheduled",
            )
            self.assertFalse(updated)

            flight = get_flight_by_id(second_flight_id, self.admin_id)
            self.assertEqual(flight["aircraft_id"], self.second_aircraft_id)
            self.assertEqual(flight["departure_time"], "2026-06-01T13:00")


if __name__ == "__main__":
    unittest.main()
