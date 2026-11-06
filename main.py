"""Загрузка страницы Gismeteo и вывод её заголовка <title> в консоль."""

import sys

import requests
from bs4 import BeautifulSoup

URL = "https://www.gismeteo.ru/weather-gorodets-4334/"
REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; WeatherGorodetsParser/1.0; "
        "+https://github.com/bubnovevgenyi-ux/weather-gorodets-v1)"
    )
}


def download_page(url: str) -> bytes:
    """Загрузить HTML-страницу с указанного URL."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Не удалось загрузить страницу {url}: {exc}") from exc

    return response.content


def extract_title(html: bytes) -> str:
    """Извлечь текст из HTML-элемента <title>."""
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")

    if title_tag is None:
        raise ValueError("В загруженном HTML не найден тег <title>.")

    return title_tag.get_text(" ", strip=True)


def main() -> int:
    """Загрузить страницу Gismeteo и вывести её заголовок."""
    try:
        html = download_page(URL)
        title = extract_title(html)
    except (RuntimeError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    print(f"Title страницы: {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
