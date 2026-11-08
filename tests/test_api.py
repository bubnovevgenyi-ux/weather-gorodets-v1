"""Проверки HTTP API и отдельной страницы документации."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import api


def make_payload() -> dict:
    return {
        "fetched_at_utc": "2026-11-08T06:00:00+00:00",
        "forecasts": {
            "today": {
                "label": "Погода сегодня",
                "source_url": "https://example.test/today/",
                "resolution": "hourly",
                "hours": {
                    "1794124800": {
                        "timestamp": 1794124800,
                        "time": "12:00",
                        "sky": "Облачно",
                        "temperature_c": 4.0,
                        "wind_speed_ms": 3.0,
                        "wind_gust_ms": 6.0,
                        "wind_direction": "СЗ",
                    }
                },
            },
            "tomorrow": {
                "label": "Погода завтра",
                "source_url": "https://example.test/tomorrow/",
                "resolution": "hourly",
                "hours": {},
            },
            "10_days": {
                "label": "Погода 10 дней",
                "source_url": "https://example.test/10-days/",
                "resolution": "daily",
                "days": {},
            },
            "2_weeks": {
                "label": "Погода 2 недели",
                "source_url": "https://example.test/2-weeks/",
                "resolution": "daily",
                "days": {},
            },
        },
    }


class WeatherApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_file = Path(self.temp_dir.name) / "weather.json"
        self.path_patcher = patch.object(api, "WEATHER_JSON_PATH", self.data_file)
        self.path_patcher.start()
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        self.client.close()
        self.path_patcher.stop()
        self.temp_dir.cleanup()

    def write_payload(self) -> dict:
        payload = make_payload()
        self.data_file.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return payload

    def test_health_without_forecast_reports_not_initialized(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "not_initialized")
        self.assertFalse(response.json()["forecast_available"])

    def test_forecast_returns_503_when_data_file_is_missing(self) -> None:
        response = self.client.get("/api/v1/forecast")
        self.assertEqual(response.status_code, 503)
        self.assertIn("detail", response.json())

    def test_forecast_returns_saved_json(self) -> None:
        expected = self.write_payload()
        response = self.client.get("/api/v1/forecast")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_period_endpoint_returns_only_requested_period(self) -> None:
        self.write_payload()
        response = self.client.get("/api/v1/forecast/today")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["period"], "today")
        self.assertEqual(body["resolution"], "hourly")
        self.assertIn("hours", body)
        self.assertNotIn("forecasts", body)

    def test_unknown_period_returns_404(self) -> None:
        self.write_payload()
        response = self.client.get("/api/v1/forecast/next_month")
        self.assertEqual(response.status_code, 404)

    def test_health_reports_available_forecast(self) -> None:
        self.write_payload()
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(response.json()["forecast_available"])
        self.assertEqual(len(response.json()["available_periods"]), 4)

    def test_api_docs_page_is_available(self) -> None:
        response = self.client.get("/api-docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Документация API", response.text)
        self.assertIn("/api/v1/forecast", response.text)

    def test_openapi_schema_contains_weather_routes(self) -> None:
        response = self.client.get("/api/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/v1/health", paths)
        self.assertIn("/api/v1/forecast", paths)
        self.assertIn("/api/v1/forecast/{period}", paths)
        self.assertIn("/api/v1/refresh", paths)

    def test_refresh_requires_token(self) -> None:
        with patch.dict(os.environ, {"WEATHER_API_REFRESH_TOKEN": "unit-test-token"}):
            response = self.client.post("/api/v1/refresh")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
