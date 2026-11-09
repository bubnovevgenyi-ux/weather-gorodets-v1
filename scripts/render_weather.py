"""Экспорт серверно отрендеренных страниц прогноза в PNG.

Сначала запустите FastAPI:
    python -m uvicorn api:app --host 127.0.0.1 --port 8000

Затем:
    python scripts/render_weather.py
    python scripts/render_weather.py --period 10_days
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PERIODS = ("today", "tomorrow", "10_days", "2_weeks")


def main() -> int:
    parser = argparse.ArgumentParser(description="Сохранить серверные HTML-прогнозы в PNG.")
    parser.add_argument(
        "--url",
        default=os.getenv("WEATHER_BASE_URL", "http://127.0.0.1:8000"),
        help="базовый URL запущенного FastAPI-сервера",
    )
    parser.add_argument("--period", choices=(*PERIODS, "all"), default="all")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    periods = PERIODS if args.period == "all" else (args.period,)
    base_url = args.url.rstrip("/")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 1400},
            device_scale_factor=2,
        )
        try:
            for period in periods:
                response = page.goto(
                    f"{base_url}/?period={period}",
                    wait_until="networkidle",
                )
                if response is None or response.status >= 400:
                    status = response.status if response is not None else "нет ответа"
                    raise RuntimeError(
                        f"FastAPI не отдал страницу для периода {period}: HTTP {status}. "
                        "Проверьте, что сервер запущен и прогноз доступен."
                    )
                page.locator(".forecast-card").wait_for(state="visible", timeout=10000)
                destination = args.output / f"weather_{period}.png"
                page.screenshot(path=str(destination), full_page=True, animations="disabled")
                print(destination)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
