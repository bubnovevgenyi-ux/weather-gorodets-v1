"""Командный запуск загрузчика прогноза погоды в Городце."""

import sys

from src.collector import (
    BASE_URL,
    FORECAST_PAGES,
    HEADERS,
    HTML_BACKUP_DIR,
    REQUEST_TIMEOUT,
    collect_forecasts,
    download_page,
)


def _print_hourly_forecast(label: str, forecast: dict) -> None:
    print(f"\n=== {label} ===")
    print("Время | Состояние неба | Температура | Ветер | Порывы | Направление")
    for weather in forecast.values():
        direction = weather.wind_direction or "—"
        print(
            f"{weather.time} | {weather.sky} | {weather.temperature_c:g} °C | "
            f"{weather.wind_speed_ms:g} м/с | {weather.wind_gust_ms:g} м/с | {direction}"
        )
    print(f"Всего временных точек: {len(forecast)}")


def _print_daily_forecast(label: str, forecast: dict) -> None:
    print(f"\n=== {label} ===")
    print("Дата | Состояние неба | Температура | Ветер | Порывы | Направление")
    for weather in forecast.values():
        if weather.temperature_min_c is not None and weather.temperature_max_c is not None:
            temperature = f"{weather.temperature_min_c:+g}…{weather.temperature_max_c:+g} °C"
        elif weather.temperature_c is not None:
            temperature = f"{weather.temperature_c:+g} °C"
        else:
            temperature = "нет данных"
        direction = weather.wind_direction or "—"
        print(
            f"{weather.date} | {weather.sky} | {temperature} | "
            f"{weather.wind_speed_ms:g} м/с | {weather.wind_gust_ms:g} м/с | {direction}"
        )
    print(f"Всего дней: {len(forecast)}")


def main() -> int:
    try:
        result = collect_forecasts()
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    print(f"Все прогнозы сохранены: {result.json_path}")
    for period, label, _url, resolution, _count in FORECAST_PAGES:
        print(f"\nЗаголовок страницы: {result.page_titles[period]}")
        if resolution == "hourly":
            _print_hourly_forecast(label, result.forecasts[period])
        else:
            _print_daily_forecast(label, result.forecasts[period])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
