"""Tests for Telegram-ready weather image generation."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.render_weather import render_period


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
            "wind_direction": "СЗ",
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
            "wind_direction": "ЮЗ",
        }
    return {
        "fetched_at_utc": "2026-11-08T06:00:00+00:00",
        "forecasts": {
            "today": {"label": "Погода сегодня", "resolution": "hourly", "hours": hours},
            "10_days": {"label": "Погода 10 дней", "resolution": "daily", "days": days},
        },
    }


class TelegramImageTests(unittest.TestCase):
    def test_daily_forecast_is_rendered_as_mobile_jpeg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "weather_10_days.jpg"
            path, size = render_period(make_payload(), "10_days", destination)
            self.assertEqual(path, destination)
            self.assertEqual(size[0], 1080)
            self.assertGreater(size[1], 1300)
            self.assertLess(size[1], 2200)
            with Image.open(path) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.mode, "RGB")

    def test_hourly_forecast_is_rendered_as_mobile_jpeg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "weather_today.jpg"
            path, size = render_period(make_payload(), "today", destination)
            self.assertEqual(path, destination)
            self.assertEqual(size[0], 1080)
            self.assertGreater(size[1], 900)
            with Image.open(path) as image:
                self.assertEqual(image.format, "JPEG")

    def test_unknown_period_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Неизвестный период"):
            render_period(make_payload(), "next_month", Path("unused.jpg"))

    def test_missing_period_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "нет прогноза"):
            render_period(make_payload(), "2_weeks", Path("unused.jpg"))


if __name__ == "__main__":
    unittest.main()
