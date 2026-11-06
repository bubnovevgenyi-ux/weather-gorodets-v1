"""Загрузка страницы Gismeteo и извлечение погоды по временным точкам."""

import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from src.parser import parse_weather_widget
from src.storage import save_forecast_json

URL = "https://www.gismeteo.ru/weather-gorodets-4334/"
REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; WeatherGorodetsParser/1.0; "
        "+https://github.com/bubnovevgenyi-ux/weather-gorodets-v1)"
    )
}
ICON_DIR = Path("assets/weather_icons")
DATA_FILE = Path("data/weather.json")


def download_page(url: str) -> bytes:
    """Загрузить HTML-страницу с указанного URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Не удалось загрузить страницу {url}: {exc}") from exc
    return response.content


def main() -> int:
    try:
        html = download_page(URL)
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        title = title_tag.get_text(" ", strip=True) if title_tag else "(title не найден)"

        forecast = parse_weather_widget(soup, ICON_DIR)
        json_path = save_forecast_json(forecast, DATA_FILE, URL)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    print(f"Title страницы: {title}")
    print(f"Получено точек прогноза: {len(forecast)}")
    print(f"JSON сохранён: {json_path}")
    print("\nВремя | Состояние неба | Температура | Ветер | Порывы | Иконка")
    saved_icons = 0
    for weather in forecast.values():
        icon_path = weather.icon_path or "не удалось сохранить SVG"
        if weather.icon_path:
            saved_icons += 1
        print(
            f"{weather.time} | {weather.sky} | {weather.temperature_c:g} °C | "
            f"{weather.wind_speed_ms:g} м/с | {weather.wind_gust_ms:g} м/с | {icon_path}"
        )
    print(f"\nСохранено иконок: {saved_icons} из {len(forecast)}")
    if saved_icons != len(forecast):
        print(
            "Предупреждение: часть SVG-символов отсутствует в HTML. "
            "Коды иконок сохранены в JSON для диагностики.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
