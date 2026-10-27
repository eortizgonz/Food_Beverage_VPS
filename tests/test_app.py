import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from io import BytesIO

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

    def test_session_expires_after_idle_timeout(self):
        with self.client.session_transaction() as session:
            session["last_activity"] = (datetime.now(timezone.utc) - timedelta(seconds=1801)).isoformat()
        response = self.client.get("/api/floor")
        self.assertEqual(response.status_code, 401)
        self.assertIn("inactividad", response.get_json()["error"])

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

    def test_copilot_chat_validation_and_contract(self):
        self.assertEqual(self.client.post("/api/copilot/chat", json={}).status_code, 400)
        with patch("app.answer_chat", return_value=("Respuesta basada en manual.", ["MAN-EQP-PU-170 · página 1"], "manuals")):
            response = self.client.post("/api/copilot/chat", json={"question": "¿Qué reviso en PU-170?", "mode": "auto"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["mode"], "manuals")
        self.assertTrue(response.get_json()["sources"])

    def test_document_upload_validation_and_contract(self):
        self.assertEqual(self.client.post("/api/documents", data={}).status_code, 400)
        with patch("app.ingest_document", return_value=2):
            response = self.client.post(
                "/api/documents",
                data={"files": [(BytesIO(b"manual de prueba"), "manual.txt"), (BytesIO(b"a,b\n1,2"), "datos.csv")]},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["total"], 2)
        self.assertEqual(response.get_json()["documents"][0]["chunks"], 2)

    def test_document_upload_rejects_unsupported_extension(self):
        response = self.client.post(
            "/api/documents", data={"files": (BytesIO(b"binary"), "program.exe")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

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

    def test_quality_dashboard_contract(self):
        response = self.client.get("/api/quality?days=30")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["period_days"], 30)
        self.assertGreater(len(payload["lots"]), 0)
        self.assertEqual(len(payload["losses"]), 5)
        self.assertLessEqual(len(payload["trend"]), 14)
        for key in ("quality", "fpy", "rejected_units", "held_lots", "lots", "total_units"):
            self.assertIn(key, payload["summary"])

    def test_oee_dashboard_contract(self):
        response = self.client.get("/api/oee?days=7")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["period_days"], 7)
        self.assertEqual(len(payload["machines"]), 20)
        self.assertLessEqual(len(payload["losses"]), 6)
        self.assertTrue(all(item["minutes"] >= 0 for item in payload["losses"]))
        for key in ("oee", "availability", "performance", "quality", "runs"):
            self.assertIn(key, payload["summary"])
        for row in payload["machines"]:
            expected = round(row["availability"] * row["performance"] * row["quality"] / 10000, 1)
            self.assertEqual(row["oee"], expected)

    def test_turn_and_oee_view_share_the_same_daily_calculation(self):
        floor = self.client.get("/api/floor").get_json()
        dashboard = self.client.get("/api/oee?days=1").get_json()
        for key in ("oee", "availability", "performance", "quality"):
            self.assertEqual(floor["oee"][key], dashboard["summary"][key])
        self.assertEqual(floor["downtime"]["minutes_today"], dashboard["summary"]["equivalent_line_downtime"])

    def test_work_shift_crud_contract_and_validation(self):
        shift = {
            "id": 4, "code": "D", "name": "Turno D", "start_time": "06:30",
            "end_time": "12:30", "planned_minutes": 360, "active": True,
        }
        with patch("app.list_work_shifts", return_value=[shift]):
            response = self.client.get("/api/shifts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()[0]["planned_minutes"], 360)

        self.assertEqual(self.client.post("/api/shifts", json={}).status_code, 400)
        with patch("app.create_work_shift", return_value=shift) as create:
            response = self.client.post("/api/shifts", json={
                "code": "d", "name": "Turno D", "start_time": "22:00",
                "end_time": "06:00", "active": True,
            })
        self.assertEqual(response.status_code, 201)
        create.assert_called_once_with("D", "Turno D", "22:00", "06:00", 480, True)

        with patch("app.update_work_shift", return_value=shift):
            response = self.client.put("/api/shifts/4", json={
                "code": "D", "name": "Turno D", "start_time": "06:30",
                "end_time": "12:30", "active": False,
            })
        self.assertEqual(response.status_code, 200)

        with patch("app.delete_work_shift", return_value=True):
            response = self.client.delete("/api/shifts/4")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["deleted"])

    def test_floor_displays_shift_resolved_from_current_time(self):
        active = {
            "id": 3, "code": "C", "name": "Turno C", "start_time": "22:00",
            "end_time": "06:00", "planned_minutes": 480, "active": True,
        }
        with patch("app.get_current_work_shift", return_value=active):
            payload = self.client.get("/api/floor").get_json()
        self.assertEqual(payload["context"]["shift"], "Turno C · 22:00–06:00")
        self.assertEqual(payload["shift"]["target_end"], "06:00")
        self.assertEqual(payload["shift"]["projected_end"], "06:27")
        self.assertEqual(payload["shift"]["work_shift_id"], 3)

    def test_downtime_filters_and_contract(self):
        response = self.client.get("/api/downtime?days=30")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["options"]["machines"]), 20)
        self.assertGreater(len(payload["events"]), 0)
        machine = payload["events"][0]["machine_code"]
        filtered = self.client.get(f"/api/downtime?days=30&machine={machine}").get_json()
        self.assertTrue(all(event["machine_code"] == machine for event in filtered["events"]))
        for event in payload["events"]:
            for key in ("started_at", "ended_at", "duration_minutes", "category", "cause", "status", "planned"):
                self.assertIn(key, event)

    def test_predictive_has_twenty_machines_and_detail(self):
        response = self.client.get("/api/predictive")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["machines"]), 20)
        self.assertEqual(
            [(item["label"], item["weight"]) for item in payload["weights"]],
            [("Vibración", 25), ("Temperatura", 20), ("Corriente", 17), ("Desviación de RPM", 14), ("Horas de uso", 12), ("Presión", 12)],
        )
        self.assertEqual(
            payload["summary"]["healthy"] + payload["summary"]["warning"] + payload["summary"]["critical"],
            20,
        )
        machine_id = payload["machines"][0]["id"]
        detail = self.client.get(f"/api/predictive/{machine_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.get_json()["factors"]), 6)
        self.assertEqual(set(detail.get_json()["limits"]), {"usage_hours", "vibration", "temperature", "current", "nominal_rpm", "pressure"})
        manuals = [machine["manual"] for machine in payload["machines"]]
        self.assertEqual(len({manual["source"] for manual in manuals}), 20)
        self.assertEqual(len({manual["diagnosis"] for manual in manuals}), 20)
        self.assertTrue(all(len(manual["causes"]) == 3 for manual in manuals))
        self.assertTrue(all(len(manual["actions"]) == 3 for manual in manuals))
        self.assertTrue(all(machine["id"] in machine["manual"]["diagnosis"] for machine in payload["machines"]))

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
