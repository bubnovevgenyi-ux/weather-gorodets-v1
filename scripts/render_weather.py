"""Save all HTML weather forecast views as PNG images.

Run from the repository root:
    python scripts/render_weather.py
    python scripts/render_weather.py --demo

Requires:
    pip install -r requirements-render.txt
    python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PERIODS = ("today", "tomorrow", "10_days", "2_weeks")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass

    def translate_path(self, path: str) -> str:
        # Веб-интерфейс обращается к API; для локального PNG-рендера
        # подменяем этот маршрут чтением уже сохранённого JSON-файла.
        if path.split("?", 1)[0] == "/api/v1/forecast":
            path = "/data/weather.json"
        return super().translate_path(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Сохранить HTML-прогнозы в PNG.")
    parser.add_argument("--demo", action="store_true", help="использовать демонстрационные данные")
    parser.add_argument("--period", choices=(*PERIODS, "all"), default="all")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    args = parser.parse_args()

    if not args.demo and not (ROOT / "data" / "weather.json").exists():
        parser.error("Нет data/weather.json. Сначала запустите python main.py или используйте --demo.")

    args.output.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    periods = PERIODS if args.period == "all" else (args.period,)
    page_url = f"http://127.0.0.1:{server.server_address[1]}/web/"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 1440, "height": 1400},
                device_scale_factor=2,
            )
            page.goto(page_url + ("?demo=1" if args.demo else ""), wait_until="networkidle")
            page.wait_for_function("window.forecastUiReady === true", timeout=10000)
            for period in periods:
                page.locator(f'[data-period="{period}"]').click()
                page.wait_for_timeout(120)
                destination = args.output / f"weather_{period}.png"
                page.screenshot(path=str(destination), full_page=True, animations="disabled")
                print(destination)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
