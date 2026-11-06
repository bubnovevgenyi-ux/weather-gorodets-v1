"""Регрессионные тесты парсинга страниц прогноза Gismeteo."""

import json
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from src.models import HourlyWeather
from src.parser import parse_weather_widget
from src.storage import save_forecasts_json


def make_weather_page(timestamp: int, temperature: int = 1) -> BeautifulSoup:
    """Собрать минимальный фрагмент с разметкой погодного виджета Gismeteo."""
    html = f"""
    <html><body>
      <div data-widget="weather-parameters">
        <div class="widget-row-datetime-time">
          <div class="row-item">
            <time-value timestamp="{timestamp}" format="H:mm"></time-value>
          </div>
        </div>
        <div data-row="icon-tooltip">
          <div class="row-item" data-tooltip="пасмурно"></div>
        </div>
        <div data-row="temperature-air">
          <div class="chart"><div class="values">
            <div class="value">
              <temperature-value value="{temperature}">{temperature}</temperature-value>
            </div>
          </div></div>
        </div>
        <div data-row="wind">
          <div class="row-item">
            <div class="wind-value wind-speed">
              <speed-value value="2">2</speed-value>
            </div>
            <div class="wind-value wind-gust">
              <speed-value value="5">5</speed-value>
            </div>
            <div class="wind-direction">СЗ</div>
          </div>
        </div>
      </div>
    </body></html>
    """
    return BeautifulSoup(html, "lxml")


class WeatherParserTests(unittest.TestCase):
    def test_today_and_tomorrow_time_comes_from_timestamp(self) -> None:
        today_timestamp = 1793912400  # 2026-11-06 00:00 Europe/Moscow
        tomorrow_timestamp = today_timestamp + 86400

        today = parse_weather_widget(make_weather_page(today_timestamp))
        tomorrow = parse_weather_widget(make_weather_page(tomorrow_timestamp, temperature=3))

        self.assertEqual(today[today_timestamp].time, "0:00")
        self.assertEqual(tomorrow[tomorrow_timestamp].time, "0:00")
        self.assertEqual(today[today_timestamp].sky, "пасмурно")
        self.assertEqual(tomorrow[tomorrow_timestamp].temperature_c, 3.0)

    def test_json_keeps_today_and_tomorrow_in_separate_sections(self) -> None:
        today_timestamp = 1793912400
        tomorrow_timestamp = today_timestamp + 86400
        today = parse_weather_widget(make_weather_page(today_timestamp))
        tomorrow = parse_weather_widget(make_weather_page(tomorrow_timestamp, temperature=3))

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "weather.json"
            save_forecasts_json(
                forecasts={"today": today, "tomorrow": tomorrow},
                labels={"today": "Погода сегодня", "tomorrow": "Погода завтра"},
                source_urls={
                    "today": "https://example.test/today/",
                    "tomorrow": "https://example.test/tomorrow/",
                },
                destination=output,
            )
            data = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(data["forecasts"]["today"]["label"], "Погода сегодня")
        self.assertEqual(data["forecasts"]["tomorrow"]["label"], "Погода завтра")
        self.assertIn(str(today_timestamp), data["forecasts"]["today"]["hours"])
        self.assertIn(str(tomorrow_timestamp), data["forecasts"]["tomorrow"]["hours"])
        self.assertNotIn("icon_path", data["forecasts"]["today"]["hours"][str(today_timestamp)])
        self.assertNotIn("icon_symbols", data["forecasts"]["tomorrow"]["hours"][str(tomorrow_timestamp)])


if __name__ == "__main__":
    unittest.main()
