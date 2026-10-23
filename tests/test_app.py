import unittest

from app import app, load_questions


class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["user_name"] = "Test User"

    def test_main_routes(self):
        for path in ("/", "/health", "/api/floor", "/api/questions", "/api/shift-handover"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_login_page_is_public_and_dashboard_is_protected(self):
        self.assertEqual(self.client.get("/login").status_code, 302)
        with self.client.session_transaction() as session:
            session.clear()
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get("/api/floor").status_code, 401)

    def test_password_recovery_pages_and_validation(self):
        self.assertEqual(self.client.get("/forgot-password").status_code, 200)
        response = self.client.post("/api/auth/forgot-password", json={"email": "invalid"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            "/api/auth/reset-password", json={"token": "invalid", "password": "short"}
        )
        self.assertEqual(response.status_code, 400)

    def test_questions_have_exact_schema(self):
        expected = {"area", "question", "answer", "action", "value", "source"}
        rows = load_questions()
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(set(row) == expected for row in rows))

    def test_answer_requires_question(self):
        response = self.client.post("/api/answer", json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_known_question(self):
        response = self.client.post(
            "/api/answer", json={"question": "¿Cuál es el cuello de botella?"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["area"], "Línea")

    def test_floor_contract(self):
        payload = self.client.get("/api/floor").get_json()
        for key in ("context", "shift", "oee", "quality", "downtime", "alerts", "actions"):
            self.assertIn(key, payload)

    def test_predictive_has_twenty_machines_and_detail(self):
        response = self.client.get("/api/predictive")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["machines"]), 20)
        self.assertEqual(
            payload["summary"]["healthy"] + payload["summary"]["warning"] + payload["summary"]["critical"],
            20,
        )
        machine_id = payload["machines"][0]["id"]
        detail = self.client.get(f"/api/predictive/{machine_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.get_json()["factors"]), 6)

    def test_unknown_action_is_rejected(self):
        self.assertEqual(self.client.get("/api/button-execute/sap").status_code, 404)

    def test_user_creation_validates_input_before_database(self):
        response = self.client.post(
            "/api/users",
            json={"name": "Test", "email": "invalid", "username": "t", "password": "short"},
        )
        self.assertEqual(response.status_code, 400)

    def test_users_endpoint_uses_database(self):
        self.assertEqual(self.client.get("/api/users").status_code, 200)


if __name__ == "__main__":
    unittest.main()
