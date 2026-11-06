"""Загрузка прогнозов Gismeteo на сегодня и завтра."""

import sys

import requests
from bs4 import BeautifulSoup

from src.parser import parse_weather_widget
from src.storage import save_forecasts_json

URL_TODAY = "https://www.gismeteo.ru/weather-gorodets-4334/"
URL_TOMORROW = "https://www.gismeteo.ru/weather-gorodets-4334/tomorrow/"
REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; WeatherGorodetsParser/1.0; "
        "+https://github.com/bubnovevgenyi-ux/weather-gorodets-v1)"
    )
}

FORECAST_PAGES = (
    ("today", "Погода сегодня", URL_TODAY),
    ("tomorrow", "Погода завтра", URL_TOMORROW),
)


def download_page(session: requests.Session, url: str) -> bytes:
    """Загрузить HTML-страницу в общей HTTP-сессии."""
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Не удалось загрузить страницу {url}: {exc}") from exc
    return response.content


def main() -> int:
    forecasts = {}
    labels = {}
    source_urls = {}
    page_titles = {}

    try:
        with requests.Session() as session:
            session.headers.update(HEADERS)

            for period, label, url in FORECAST_PAGES:
                html = download_page(session, url)
                soup = BeautifulSoup(html, "lxml")

                title_tag = soup.find("title")
                page_titles[period] = (
                    title_tag.get_text(" ", strip=True)
                    if title_tag
                    else "(title не найден)"
                )

                forecasts[period] = parse_weather_widget(soup)
                labels[period] = label
                source_urls[period] = url

        json_path = save_forecasts_json(
            forecasts=forecasts,
            labels=labels,
            source_urls=source_urls,
        )
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    print(f"Прогнозы сохранены: {json_path}")
    for period, label, _url in FORECAST_PAGES:
        forecast = forecasts[period]
        print(f"\n=== {label} ===")
        print(f"Заголовок страницы: {page_titles[period]}")
        print("Время | Состояние неба | Температура | Ветер | Порывы | Направление")
        for weather in forecast.values():
            direction = weather.wind_direction or "—"
            print(
                f"{weather.time} | {weather.sky} | {weather.temperature_c:g} °C | "
                f"{weather.wind_speed_ms:g} м/с | "
                f"{weather.wind_gust_ms:g} м/с | {direction}"
            )
        print(f"Всего временных точек: {len(forecast)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
