import os
import tempfile
import unittest

from airport_app import create_app
from airport_app.db import get_user_for_login


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        os.environ["AIRPORT_DATABASE"] = os.path.join(
            self.temp_dir.name, "test_airport.sqlite"
        )
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self):
        os.environ.pop("AIRPORT_DATABASE", None)
        self.temp_dir.cleanup()

    def test_admin_register_and_login(self):
        register_response = self.client.post(
            "/admin/register",
            data={
                "full_name": "Admin User",
                "username": "admin",
                "password": "secret",
            },
        )

        self.assertEqual(register_response.status_code, 302)
        self.assertIn("/admin/login", register_response.headers["Location"])

        with self.app.app_context():
            user = get_user_for_login("admin", "admin")
            self.assertIsNotNone(user)
            self.assertEqual(user["role"], "admin")

        login_response = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "secret"},
        )

        self.assertEqual(login_response.status_code, 302)
        self.assertIn("/admin/", login_response.headers["Location"])

    def test_pilot_register_and_login(self):
        register_response = self.client.post(
            "/pilot/register",
            data={
                "full_name": "Pilot User",
                "rank": "Captain",
                "username": "pilot",
                "password": "secret",
            },
        )

        self.assertEqual(register_response.status_code, 302)
        self.assertIn("/pilot/login", register_response.headers["Location"])

        with self.app.app_context():
            user = get_user_for_login("pilot", "pilot")
            self.assertIsNotNone(user)
            self.assertEqual(user["role"], "pilot")
            self.assertEqual(user["rank"], "Captain")

        login_response = self.client.post(
            "/pilot/login",
            data={"username": "pilot", "password": "secret"},
        )

        self.assertEqual(login_response.status_code, 302)
        self.assertIn("/pilot/dashboard", login_response.headers["Location"])

    def test_invalid_login_does_not_create_session(self):
        response = self.client.post(
            "/admin/login",
            data={"username": "missing", "password": "wrong"},
        )

        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)


if __name__ == "__main__":
    unittest.main()
