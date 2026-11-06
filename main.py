"""Загрузка страницы Gismeteo и извлечение погоды по временным точкам."""

import sys

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
DATA_FILE = "data/weather.json"


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

        forecast = parse_weather_widget(soup)
        json_path = save_forecast_json(forecast, source_url=URL)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    print(f"Title страницы: {title}")
    print(f"Получено точек прогноза: {len(forecast)}")
    print(f"JSON сохранён: {json_path}")
    print("\nВремя | Состояние неба | Температура | Ветер | Порывы | Направление")
    for weather in forecast.values():
        direction = weather.wind_direction or "—"
        print(
            f"{weather.time} | {weather.sky} | {weather.temperature_c:g} °C | "
            f"{weather.wind_speed_ms:g} м/с | {weather.wind_gust_ms:g} м/с | {direction}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
