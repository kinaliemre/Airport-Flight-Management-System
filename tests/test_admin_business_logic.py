import os
import tempfile
import unittest

from airport_app import create_app
from airport_app.db import (
    create_admin,
    create_aircraft,
    create_airport,
    create_route,
    delete_aircraft,
    get_aircraft_by_id,
    list_routes,
    update_aircraft,
    update_airport,
    update_route,
)


class AdminBusinessLogicTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        os.environ["AIRPORT_DATABASE"] = os.path.join(
            self.temp_dir.name, "test_airport.sqlite"
        )
        self.app = create_app()
        self.app.config.update(TESTING=True)

    def tearDown(self):
        os.environ.pop("AIRPORT_DATABASE", None)
        self.temp_dir.cleanup()

    def test_aircraft_full_crud_business_logic(self):
        with self.app.app_context():
            admin_id = create_admin("Admin User", "admin", "secret")
            aircraft_id = create_aircraft(
                admin_id, "TC-ONE", "Airbus A320", 180, "30 rows"
            )
            self.assertIsNotNone(aircraft_id)

            updated = update_aircraft(
                admin_id, aircraft_id, "TC-TWO", "Boeing 737", 160, "27 rows"
            )
            self.assertTrue(updated)

            aircraft = get_aircraft_by_id(aircraft_id, admin_id)
            self.assertEqual(aircraft["name"], "TC-TWO")
            self.assertEqual(aircraft["capacity"], 160)

            deleted = delete_aircraft(admin_id, aircraft_id)
            self.assertTrue(deleted)
            self.assertIsNone(get_aircraft_by_id(aircraft_id, admin_id))

    def test_airport_and_route_business_logic(self):
        with self.app.app_context():
            admin_id = create_admin("Admin User", "admin", "secret")
            departure_id = create_airport(
                admin_id, "Istanbul Airport", "Istanbul", "Turkiye", "IST"
            )
            destination_id = create_airport(
                admin_id, "Esenboga Airport", "Ankara", "Turkiye", "ESB"
            )
            self.assertIsNotNone(departure_id)
            self.assertIsNotNone(destination_id)

            self.assertTrue(
                update_airport(
                    admin_id,
                    destination_id,
                    "Esenboga Airport",
                    "Ankara",
                    "Turkiye",
                    "ANK",
                )
            )

            route_id = create_route(admin_id, departure_id, destination_id, 65)
            self.assertIsNotNone(route_id)
            self.assertTrue(
                update_route(admin_id, route_id, departure_id, destination_id, 70)
            )

            routes = list_routes(admin_id)
            self.assertEqual(len(routes), 1)
            self.assertEqual(routes[0]["destination_iata"], "ANK")
            self.assertEqual(routes[0]["estimated_duration_minutes"], 70)


if __name__ == "__main__":
    unittest.main()
