"""Проверки JSON API, серверного HTML-рендеринга и документации."""

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
                "days": {
                    "1794124800": {
                        "timestamp": 1794124800,
                        "date": "2026-11-08",
                        "sky": "Ясно",
                        "temperature_c": None,
                        "temperature_min_c": 1.0,
                        "temperature_max_c": 6.0,
                        "wind_speed_ms": 2.0,
                        "wind_gust_ms": 4.0,
                        "wind_direction": "С",
                    }
                },
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

    def test_startup_collects_forecast_when_cache_is_missing(self) -> None:
        with patch.object(api, "collect_forecasts") as collect:
            with TestClient(api.app):
                collect.assert_called_once_with(self.data_file)

    def test_startup_does_not_collect_when_cache_exists(self) -> None:
        self.write_payload()
        with patch.object(api, "collect_forecasts") as collect:
            with TestClient(api.app):
                collect.assert_not_called()

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

    def test_homepage_renders_hourly_forecast_on_server(self) -> None:
        self.write_payload()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Погода сегодня", response.text)
        self.assertIn("Облачно", response.text)
        self.assertIn('href="/docs"', response.text)
        self.assertIn("12:00", response.text)
        self.assertIn("4°", response.text)
        self.assertIn("<svg", response.text)
        self.assertNotIn("app.js", response.text)

    def test_homepage_renders_daily_forecast_on_server(self) -> None:
        self.write_payload()
        response = self.client.get("/?period=10_days")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Прогноз на каждый день", response.text)
        self.assertIn("Ясно", response.text)
        self.assertIn("+1° / +6°", response.text)
        self.assertIn("daily-grid", response.text)

    def test_homepage_is_available_without_forecast(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Пока нет данных прогноза", response.text)
        self.assertIn("POST /api/v1/refresh", response.text)

    def test_homepage_rejects_unknown_period(self) -> None:
        response = self.client.get("/?period=next_month")
        self.assertEqual(response.status_code, 404)

    def test_static_stylesheet_is_served(self) -> None:
        response = self.client.get("/static/styles.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn(".forecast-card", response.text)

    def test_fastapi_native_documentation_is_available(self) -> None:
        docs = self.client.get("/docs")
        redoc = self.client.get("/redoc")
        self.assertEqual(docs.status_code, 200)
        self.assertEqual(redoc.status_code, 200)
        self.assertIn("/openapi.json", docs.text)
        self.assertEqual(self.client.get("/api-docs").status_code, 404)

    def test_openapi_schema_contains_weather_routes(self) -> None:
        response = self.client.get("/openapi.json")
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

    def test_health_exposes_refresh_configuration_without_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(api, "ENV_FILE", Path(temp_dir) / ".env"):
                with patch.dict(os.environ, {}, clear=True):
                    response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["refresh_enabled"])

    def test_refresh_token_is_loaded_from_dotenv_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "WEATHER_API_REFRESH_TOKEN=dotenv-test-token\n",
                encoding="utf-8",
            )
            with patch.object(api, "ENV_FILE", env_file):
                with patch.dict(os.environ, {}, clear=True):
                    self.assertEqual(api._get_refresh_token(), "dotenv-test-token")

    def test_refresh_accepts_token_from_dotenv_file(self) -> None:
        payload = self.write_payload()
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "WEATHER_API_REFRESH_TOKEN=dotenv-test-token\n",
                encoding="utf-8",
            )
            with patch.object(api, "ENV_FILE", env_file):
                with patch.dict(os.environ, {}, clear=True):
                    with patch.object(api, "collect_forecasts") as collect:
                        response = self.client.post(
                            "/api/v1/refresh",
                            headers={"X-Refresh-Token": "dotenv-test-token"},
                        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        collect.assert_called_once_with(destination=self.data_file)

    def test_refresh_without_token_has_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            with patch.object(api, "ENV_FILE", env_file):
                with patch.dict(os.environ, {}, clear=True):
                    response = self.client.post("/api/v1/refresh")
        self.assertEqual(response.status_code, 503)
        self.assertIn(".env", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
