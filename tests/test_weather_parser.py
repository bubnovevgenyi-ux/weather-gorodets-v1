"""Регрессионные тесты почасовых и дневных прогнозов Gismeteo."""

import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from src.parser import parse_daily_weather_widget, parse_weather_widget
from src.storage import save_forecasts_json


def make_hourly_page(timestamp: int, temperature: int = 1) -> BeautifulSoup:
    html = f"""
    <html><body>
      <div data-widget="weather-parameters">
        <div class="widget-row-datetime-time"><div class="row-item">
          <time-value timestamp="{timestamp}" format="H:mm"></time-value>
        </div></div>
        <div data-row="icon-tooltip"><div class="row-item" data-tooltip="пасмурно"></div></div>
        <div data-row="temperature-air"><div class="chart"><div class="values"><div class="value">
          <temperature-value value="{temperature}">{temperature}</temperature-value>
        </div></div></div></div>
        <div data-row="wind"><div class="row-item">
          <div class="wind-value wind-speed"><speed-value value="2">2</speed-value></div>
          <div class="wind-value wind-gust"><speed-value value="5">5</speed-value></div>
          <div class="wind-direction">СЗ</div>
        </div></div>
      </div>
    </body></html>
    """
    return BeautifulSoup(html, "lxml")


def make_daily_page(start_timestamp: int, days: int) -> BeautifulSoup:
    start_date = datetime.fromtimestamp(
        start_timestamp, tz=timezone.utc
    ).astimezone(ZoneInfo("Europe/Moscow")).date()
    month_labels = (
        "янв", "фев", "мар", "апр", "май", "июн",
        "июл", "авг", "сен", "окт", "нояб", "дек",
    )
    dates = []
    skies = []
    temperatures = []
    winds = []
    for index in range(days):
        forecast_date = start_date + timedelta(days=index)
        date_label = (
            f"{forecast_date.day} {month_labels[forecast_date.month - 1]}"
            if index == 0
            else str(forecast_date.day)
        )
        dates.append(
            '<a class="row-item link link-hover" href="#">'
            f'<div class="day">день</div><div class="date">{date_label}</div>'
            '</a>'
        )
        skies.append(
            f'<div class="row-item" data-tooltip="облачно, день {index + 1}"></div>'
        )
        low, high = -2 + index % 4, 3 + index % 5
        temperatures.append(
            '<div class="value">'
            f'<div class="maxt"><temperature-value value="{high}">+{high}</temperature-value></div>'
            f'<div class="mint"><temperature-value value="{low}">{low}</temperature-value></div>'
            '</div>'
        )
        winds.append(
            '<div class="row-item">'
            '<div class="wind-value wind-speed"><speed-value value="2">2</speed-value></div>'
            '<div class="wind-value wind-gust"><speed-value value="6">6</speed-value></div>'
            '<div class="wind-direction">СЗ</div>'
            '</div>'
        )

    html = f"""
    <html><body>
      <div data-widget="weather-parameters">
        <div class="widget-row widget-row-date">{''.join(dates)}</div>
        <div class="widget-row widget-row-icon" data-row="icon-tooltip">{''.join(skies)}</div>
        <div class="widget-row widget-row-chart" data-row="temperature-air">
          <div class="chart"><div class="values">{''.join(temperatures)}</div></div>
        </div>
        <div class="widget-row widget-row-wind" data-row="wind">{''.join(winds)}</div>
      </div>
    </body></html>
    """
    return BeautifulSoup(html, "lxml")

class WeatherParserTests(unittest.TestCase):
    def test_hourly_forecast_time_comes_from_timestamp(self) -> None:
        timestamp = 1793912400
        forecast = parse_weather_widget(make_hourly_page(timestamp))
        self.assertEqual(forecast[timestamp].time, "0:00")
        self.assertEqual(forecast[timestamp].sky, "пасмурно")

    def test_daily_parser_returns_exactly_ten_days(self) -> None:
        timestamp = 1793998800
        with patch("src.parser._today_local_date", return_value=date(2026, 11, 7)):
            forecast = parse_daily_weather_widget(
                make_daily_page(timestamp, 10), expected_days=10
            )
        self.assertEqual(len(forecast), 10)
        record = forecast[timestamp]
        self.assertEqual(record.temperature_min_c, -2.0)
        self.assertEqual(record.temperature_max_c, 3.0)
        self.assertEqual(record.wind_speed_ms, 2.0)
        self.assertEqual(record.wind_gust_ms, 6.0)

    def test_daily_parser_returns_exactly_fourteen_days(self) -> None:
        timestamp = 1793998800
        with patch("src.parser._today_local_date", return_value=date(2026, 11, 7)):
            forecast = parse_daily_weather_widget(
                make_daily_page(timestamp, 14), expected_days=14
            )
        self.assertEqual(len(forecast), 14)
        self.assertEqual(list(forecast.values())[0].date, "2026-11-07")

    def test_json_saves_hourly_and_daily_sections_separately(self) -> None:
        timestamp = 1793998800
        hourly = parse_weather_widget(make_hourly_page(1793912400))
        with patch("src.parser._today_local_date", return_value=date(2026, 11, 7)):
            ten_days = parse_daily_weather_widget(
                make_daily_page(timestamp, 10), expected_days=10
            )
            two_weeks = parse_daily_weather_widget(
                make_daily_page(timestamp, 14), expected_days=14
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "weather.json"
            save_forecasts_json(
                forecasts={
                    "today": hourly,
                    "10_days": ten_days,
                    "2_weeks": two_weeks,
                },
                labels={
                    "today": "Погода сегодня",
                    "10_days": "Погода 10 дней",
                    "2_weeks": "Погода 2 недели",
                },
                source_urls={
                    "today": "https://example.test/today/",
                    "10_days": "https://example.test/10-days/",
                    "2_weeks": "https://example.test/2-weeks/",
                },
                destination=output,
            )
            data = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn("hours", data["forecasts"]["today"])
        self.assertNotIn("days", data["forecasts"]["today"])
        self.assertEqual(data["forecasts"]["10_days"]["resolution"], "daily")
        self.assertEqual(len(data["forecasts"]["10_days"]["days"]), 10)
        self.assertEqual(data["forecasts"]["2_weeks"]["label"], "Погода 2 недели")
        self.assertEqual(len(data["forecasts"]["2_weeks"]["days"]), 14)


if __name__ == "__main__":
    unittest.main()
