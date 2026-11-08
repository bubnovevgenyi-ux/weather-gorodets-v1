"""Общий сборщик погодных данных Gismeteo для CLI и HTTP API."""

import sys
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .parser import parse_daily_weather_widget, parse_weather_widget
from .storage import save_forecasts_json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://www.gismeteo.ru/weather-gorodets-4334/"
REQUEST_TIMEOUT = 15
HTML_BACKUP_DIR = PROJECT_ROOT / "data" / "html_backup"
WEATHER_JSON_PATH = PROJECT_ROOT / "data" / "weather.json"

HEADERS = {
    "Accept": "*/*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0.0.0 YaBrowser/26.10.0.0 Safari/537.36"
    ),
}

FORECAST_PAGES = (
    ("today", "Погода сегодня", BASE_URL, "hourly", 0),
    ("tomorrow", "Погода завтра", BASE_URL + "tomorrow/", "hourly", 0),
    ("10_days", "Погода 10 дней", BASE_URL + "10-days/", "daily", 10),
    ("2_weeks", "Погода 2 недели", BASE_URL + "2-weeks/", "daily", 14),
)


@dataclass(frozen=True)
class CollectionResult:
    """Результат полного цикла загрузки и разбора четырёх прогнозов."""

    forecasts: dict
    labels: dict[str, str]
    source_urls: dict[str, str]
    page_titles: dict[str, str]
    json_path: Path


def _save_html_backup(html: bytes, destination: Path) -> None:
    """Атомарно сохранить HTML, не повреждая предыдущую копию при сбое записи."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = destination.with_suffix(destination.suffix + ".tmp")
    try:
        temporary_file.write_bytes(html)
        temporary_file.replace(destination)
    except OSError:
        try:
            temporary_file.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def download_page(
    session: requests.Session,
    url: str,
    backup_path: Path,
) -> bytes:
    """Загрузить HTML и сохранить копию; при сетевой ошибке использовать кэш."""
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        html = response.content
        if not html:
            raise requests.RequestException("Сервер вернул пустой ответ.")
    except requests.RequestException as exc:
        try:
            cached_html = backup_path.read_bytes()
        except OSError as cache_exc:
            raise RuntimeError(
                f"Не удалось загрузить страницу {url}: {exc}. "
                f"Резервная копия {backup_path} недоступна: {cache_exc}"
            ) from exc

        if not cached_html:
            raise RuntimeError(
                f"Не удалось загрузить страницу {url}: {exc}. "
                f"Резервная копия {backup_path} пуста."
            ) from exc

        print(
            f"Предупреждение: {url} недоступна ({exc}). "
            f"Используется сохранённая копия: {backup_path}",
            file=sys.stderr,
        )
        return cached_html

    try:
        _save_html_backup(html, backup_path)
    except OSError as exc:
        raise RuntimeError(
            f"Страница загружена, но не удалось сохранить её копию "
            f"в {backup_path}: {exc}"
        ) from exc

    print(f"HTML сохранён: {backup_path}")
    return html


def collect_forecasts(
    destination: Path = WEATHER_JSON_PATH,
) -> CollectionResult:
    """Загрузить четыре страницы, разобрать прогнозы и записать общий JSON."""
    forecasts = {}
    labels = {}
    source_urls = {}
    page_titles = {}

    with requests.Session() as session:
        session.headers.update(HEADERS)

        for period, label, url, resolution, expected_count in FORECAST_PAGES:
            backup_path = HTML_BACKUP_DIR / f"{period}.html"
            html = download_page(session, url, backup_path)
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            page_titles[period] = (
                title_tag.get_text(" ", strip=True)
                if title_tag
                else "(title не найден)"
            )

            if resolution == "hourly":
                forecast = parse_weather_widget(soup)
            else:
                forecast = parse_daily_weather_widget(
                    soup,
                    expected_days=expected_count,
                )

            forecasts[period] = forecast
            labels[period] = label
            source_urls[period] = url

    json_path = save_forecasts_json(
        forecasts=forecasts,
        labels=labels,
        source_urls=source_urls,
        destination=destination,
    )
    return CollectionResult(
        forecasts=forecasts,
        labels=labels,
        source_urls=source_urls,
        page_titles=page_titles,
        json_path=json_path,
    )
