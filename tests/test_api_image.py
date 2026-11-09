"""HTTP tests for FastAPI weather image endpoint."""

import unittest
from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

import api


def make_payload() -> dict:
    hours = {}
    days = {}
    for index in range(8):
        timestamp = 1794124800 + index * 10800
        hours[str(timestamp)] = {
            "timestamp": timestamp,
            "time": f"{index * 3:02d}:00",
            "sky": "Небольшой дождь" if index % 2 else "Облачно",
            "temperature_c": 3 + index,
            "wind_speed_ms": 2.0,
            "wind_gust_ms": 5.0,
        }
    for index in range(10):
        timestamp = 1794124800 + index * 86400
        days[str(timestamp)] = {
            "timestamp": timestamp,
            "date": f"2026-11-{8 + index:02d}",
            "sky": "Ясно" if index % 2 else "Облачно",
            "temperature_c": None,
            "temperature_min_c": -2 + index,
            "temperature_max_c": 3 + index,
            "wind_speed_ms": 3.0,
            "wind_gust_ms": 6.0,
        }
    return {
        "fetched_at_utc": "2026-11-08T06:00:00+00:00",
        "forecasts": {
            "today": {"label": "Погода сегодня", "resolution": "hourly", "hours": hours},
            "10_days": {"label": "Погода 10 дней", "resolution": "daily", "days": days},
        },
    }


class ForecastImageEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client_context = patch.object(api, "collect_forecasts")
        self.client_context.start()
        self.addCleanup(self.client_context.stop)
        self.client = TestClient(api.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_daily_forecast_image_returns_jpeg(self) -> None:
        with patch.object(api, "_read_forecast", return_value=make_payload()):
            response = self.client.get("/api/v1/forecast/10_days/image")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertIn('filename="weather_10_days.jpg"', response.headers["content-disposition"])
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.width, 1080)
            self.assertGreater(image.height, 1300)

    def test_hourly_forecast_image_returns_jpeg(self) -> None:
        with patch.object(api, "_read_forecast", return_value=make_payload()):
            response = self.client.get("/api/v1/forecast/today/image")

        self.assertEqual(response.status_code, 200)
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.width, 1080)

    def test_unknown_period_returns_404(self) -> None:
        response = self.client.get("/api/v1/forecast/next_month/image")
        self.assertEqual(response.status_code, 404)

    def test_period_without_forecast_returns_404(self) -> None:
        with patch.object(api, "_read_forecast", return_value={"forecasts": {}}):
            response = self.client.get("/api/v1/forecast/2_weeks/image")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
