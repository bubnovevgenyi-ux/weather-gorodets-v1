"""Извлечение погодных показателей из виджета Gismeteo."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

from .models import HourlyWeather, WeatherByTimestamp

WIDGET_SELECTOR = '[data-widget="weather-parameters"]'
FORECAST_TIMEZONE = ZoneInfo("Europe/Moscow")


def _number_from_tag(tag: Tag | None, field_name: str) -> float:
    if tag is None:
        raise ValueError(f"Не найдено значение поля «{field_name}».")
    raw = tag.get("value")
    if raw is None:
        raw = tag.get_text(strip=True)
    try:
        return float(str(raw).replace("−", "-").replace(",", ".").strip())
    except ValueError as exc:
        raise ValueError(f"Некорректное значение поля «{field_name}»: {raw!r}") from exc


def _format_forecast_time(timestamp: int) -> str:
    """Преобразовать Unix timestamp в локальное время Городца формата H:MM."""
    local_time = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).astimezone(FORECAST_TIMEZONE)
    return f"{local_time.hour}:{local_time.minute:02d}"


def parse_weather_widget(page_soup: BeautifulSoup) -> WeatherByTimestamp:
    """Распарсить виджет, сопоставляя строки по индексу временной точки.

    Время формируется по timestamp в часовом поясе Europe/Moscow, а не
    читается из текста кастомного HTML-тега <time-value>.
    Результат — dict с Unix timestamp в качестве ключа: средний O(1) доступ.
    """
    widget = page_soup.select_one(WIDGET_SELECTOR)
    if widget is None:
        raise ValueError(f"Не найден блок Gismeteo {WIDGET_SELECTOR}.")

    time_row = widget.select_one(".widget-row-datetime-time")
    sky_row = widget.select_one('[data-row="icon-tooltip"]')
    temp_row = widget.select_one('[data-row="temperature-air"]')
    wind_row = widget.select_one('[data-row="wind"]')
    if any(row is None for row in (time_row, sky_row, temp_row, wind_row)):
        raise ValueError("В погодном блоке отсутствует один из обязательных рядов.")

    time_cells = time_row.select(".row-item")
    sky_cells = sky_row.select(":scope > .row-item")
    temp_cells = temp_row.select(".chart .values .value")
    wind_cells = wind_row.select(":scope > .row-item")
    counts = {
        "время": len(time_cells),
        "небо": len(sky_cells),
        "температура": len(temp_cells),
        "ветер": len(wind_cells),
    }
    expected = counts["время"]
    if expected == 0 or any(count != expected for count in counts.values()):
        raise ValueError(f"Число элементов погодных рядов не совпадает: {counts}")

    forecast: WeatherByTimestamp = {}
    for index, time_cell in enumerate(time_cells):
        time_tag = time_cell.select_one("time-value[timestamp]")
        if time_tag is None:
            raise ValueError(f"Для точки №{index + 1} отсутствует timestamp.")

        try:
            timestamp = int(time_tag["timestamp"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Некорректный timestamp для точки №{index + 1}.") from exc

        if timestamp in forecast:
            raise ValueError(f"Повторяющийся timestamp: {timestamp}")

        wind_cell = wind_cells[index]
        direction_tag = wind_cell.select_one(".wind-direction")

        forecast[timestamp] = HourlyWeather(
            timestamp=timestamp,
            time=_format_forecast_time(timestamp),
            sky=str(sky_cells[index].get("data-tooltip", "")).strip(),
            temperature_c=_number_from_tag(
                temp_cells[index].select_one("temperature-value"), "температура"
            ),
            wind_speed_ms=_number_from_tag(
                wind_cell.select_one(".wind-speed speed-value"), "скорость ветра"
            ),
            wind_gust_ms=_number_from_tag(
                wind_cell.select_one(".wind-gust speed-value"), "порывы ветра"
            ),
            wind_direction=direction_tag.get_text(" ", strip=True) if direction_tag else None,
        )

    return forecast
