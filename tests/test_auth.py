import os
import tempfile
import unittest

from airport_app import create_app
from airport_app.db import (
    create_admin,
    create_pilot,
    get_pilot_by_user_id,
    get_user_for_login,
    verify_user_password,
)


class AuthBusinessLogicTestCase(unittest.TestCase):
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

    def test_create_admin_and_verify_password(self):
        with self.app.app_context():
            admin_id = create_admin("Admin User", "admin", "secret")
            self.assertIsNotNone(admin_id)

            user = get_user_for_login("admin", "admin")
            self.assertIsNotNone(user)
            self.assertEqual(user["role"], "admin")
            self.assertTrue(verify_user_password(user, "secret"))
            self.assertFalse(verify_user_password(user, "wrong"))

    def test_create_pilot_stores_rank_and_owner(self):
        with self.app.app_context():
            admin_id = create_admin("Admin User", "admin", "secret")
            pilot_user_id = create_pilot(
                "Pilot User",
                "pilot",
                "secret",
                "Captain",
                owner_user_id=admin_id,
            )
            self.assertIsNotNone(pilot_user_id)

            pilot = get_pilot_by_user_id(pilot_user_id)
            self.assertEqual(pilot["rank"], "Captain")
            self.assertEqual(pilot["full_name"], "Pilot User")

            user = get_user_for_login("pilot", "pilot")
            self.assertTrue(verify_user_password(user, "secret"))

    def test_duplicate_username_is_rejected(self):
        with self.app.app_context():
            first_id = create_admin("First Admin", "same", "secret")
            second_id = create_pilot("Pilot User", "same", "secret", "Captain")

            self.assertIsNotNone(first_id)
            self.assertIsNone(second_id)


if __name__ == "__main__":
    unittest.main()
