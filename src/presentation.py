"""Подготовка погодных данных для серверного HTML-рендеринга."""

from __future__ import annotations

import html
import math
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any

MOSCOW = ZoneInfo("Europe/Moscow")
MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
MONTHS_SHORT = (
    "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
)
WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
WEEKDAYS_LONG = (
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
)


def _number(value: Any) -> float | None:
    """Преобразовать значение в конечное число; некорректные значения пропустить."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def format_temperature(value: float | None) -> str:
    """Форматировать температуру со знаком и единицей измерения."""
    if value is None:
        return "—°"
    rounded = int(value) if value.is_integer() else round(value, 1)
    prefix = "+" if value > 0 else ""
    return f"{prefix}{rounded}°"


def _temperature_band(row: dict[str, Any]) -> tuple[float | None, float | None]:
    single = _number(row.get("temperature_c"))
    low = _number(row.get("temperature_min_c"))
    high = _number(row.get("temperature_max_c"))
    return (single if low is None else low, single if high is None else high)


def _row_date(row: dict[str, Any]) -> date | None:
    raw_date = row.get("date")
    if raw_date:
        try:
            return date.fromisoformat(str(raw_date))
        except ValueError:
            pass
    timestamp = _number(row.get("timestamp"))
    if timestamp is not None:
        return datetime.fromtimestamp(timestamp, MOSCOW).date()
    return None


def _format_date(value: date, *, long_month: bool = False, weekday: bool = False) -> str:
    month = MONTHS[value.month - 1] if long_month else MONTHS_SHORT[value.month - 1]
    prefix = f"{WEEKDAYS[value.weekday()]}, " if weekday else ""
    return f"{prefix}{value.day} {month}"


def _weather_icon(description: str | None) -> str:
    """Вернуть SVG-иконку по типу погоды; пользовательские строки в SVG не вставляются."""
    value = (description or "").casefold()
    cloud = (
        '<path d="M13 40h37a11 11 0 0 0 1-22 17 17 0 0 0-32-3 13 13 0 0 0-6 25Z" '
        'fill="#80a9c5"/>'
    )
    shape = cloud
    if "гроз" in value:
        shape += '<path d="m34 35-8 11h7l-3 9 13-15h-8l4-5Z" fill="#f0b44e"/>'
    elif "снег" in value:
        shape += (
            '<g stroke="#45a8d8" stroke-width="2.4" stroke-linecap="round">'
            '<path d="M22 47v9m-4-7 8 5m0-5-8 5M43 47v9m-4-7 8 5m0-5-8 5"/>'
            '</g>'
        )
    elif "дожд" in value or "морос" in value:
        shape += (
            '<g stroke="#45a8d8" stroke-width="3" stroke-linecap="round">'
            '<path d="m23 46-3 6m15-6-3 6m15-6-3 6"/>'
            '</g>'
        )
    elif "ясно" in value or "солнеч" in value:
        shape = (
            '<circle cx="32" cy="26" r="15" fill="#f7bd55"/>'
            '<g stroke="#f7bd55" stroke-width="3" stroke-linecap="round">'
            '<path d="M32 3v6M32 43v6M9 26h6M49 26h6M16 10l5 5m22 22 5 5m0-32-5 5M21 37l-5 5"/>'
            '</g>'
        )
    elif "перемен" in value:
        shape = '<circle cx="43" cy="16" r="11" fill="#f7bd55"/>' + cloud
    return (
        '<svg class="weather-svg" viewBox="0 0 64 58" aria-hidden="true">'
        + shape
        + "</svg>"
    )


def _chart_svg(records: list[dict[str, Any]], daily: bool) -> str:
    """Построить SVG-график температуры на сервере."""
    points_data: list[tuple[float, str]] = []
    for row in records:
        low, high = _temperature_band(row)
        value = (low + high) / 2 if daily and low is not None and high is not None else (
            _number(row.get("temperature_c"))
        )
        if value is None:
            continue
        if daily:
            day = _row_date(row)
            label = _format_date(day) if day else ""
        else:
            label = str(row.get("time") or "")
        points_data.append((value, label))

    if not points_data:
        return ""

    values = [item[0] for item in points_data]
    minimum, maximum = min(values), max(values)
    span = max(1.0, maximum - minimum)
    left, right, top, bottom = 22.0, 978.0, 15.0, 72.0
    points = []
    for index, (value, label) in enumerate(points_data):
        x = 500.0 if len(points_data) == 1 else left + (right - left) * index / (len(points_data) - 1)
        y = bottom - ((value - minimum) / span) * (bottom - top)
        points.append((x, y, value, label))

    line = " ".join(
        ("M" if index == 0 else "L") + f"{x:.2f},{y:.2f}"
        for index, (x, y, _value, _label) in enumerate(points)
    )
    first_x, first_y = points[0][0], points[0][1]
    last_x, last_y = points[-1][0], points[-1][1]
    area = f"{line} L{last_x:.2f},{bottom + 9:.2f} L{first_x:.2f},{bottom + 9:.2f} Z"

    guides = "".join(
        f'<line x1="{left}" y1="{top + i * (bottom - top) / 2:.2f}" '
        f'x2="{right}" y2="{top + i * (bottom - top) / 2:.2f}" '
        'stroke="#eaf1f6" stroke-dasharray="4 7"/>'
        for i in range(3)
    )
    marks = []
    for x, y, value, label in points:
        temperature = f"{value:+.1f}".replace(".0", "") + "°"
        marks.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.5" fill="#fff" '
            'stroke="#1686ce" stroke-width="3"/>'
            f'<text x="{x:.2f}" y="{y - 12:.2f}" text-anchor="middle" '
            'fill="#4a7596" font-size="12" font-weight="700">'
            f'{html.escape(temperature)}</text>'
            f'<text x="{x:.2f}" y="94" text-anchor="middle" '
            'fill="#9aabba" font-size="10">{html.escape(label)}</text>'
        )
    return (
        '<svg viewBox="0 0 1000 100" preserveAspectRatio="none" role="img" '
        'aria-label="Изменение температуры">'
        '<defs><linearGradient id="tempFill" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset="0" stop-color="#52b8e6" stop-opacity=".22"/>'
        '<stop offset="1" stop-color="#52b8e6" stop-opacity="0"/>'
        '</linearGradient></defs>'
        + guides
        + f'<path d="{area}" fill="url(#tempFill)"/>'
        + f'<path d="{line}" fill="none" stroke="#218ed0" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        + "".join(marks)
        + "</svg>"
    )


def build_forecast_view(payload: dict[str, Any], period: str) -> dict[str, Any] | None:
    """Собрать безопасную и готовую к отображению модель выбранного прогноза."""
    forecast = (payload.get("forecasts") or {}).get(period)
    if not isinstance(forecast, dict):
        return None

    daily = forecast.get("resolution") == "daily"
    collection_key = "days" if daily else "hours"
    source_records = forecast.get(collection_key) or {}
    if isinstance(source_records, dict):
        records = sorted(
            (row for row in source_records.values() if isinstance(row, dict)),
            key=lambda row: _number(row.get("timestamp")) or 0,
        )
    else:
        records = []

    if not records:
        return None

    bands = [_temperature_band(row) for row in records]
    lows = [low for low, _high in bands if low is not None]
    highs = [high for _low, high in bands if high is not None]
    first_low, first_high = bands[0]

    card_records = []
    for row, (low, high) in zip(records, bands):
        if daily:
            day = _row_date(row)
            date_or_time = _format_date(day, weekday=True) if day else "—"
        else:
            date_or_time = str(row.get("time") or "—")

        if daily and low is not None and high is not None and low != high:
            temperature = f"{format_temperature(low)} / {format_temperature(high)}"
        else:
            temperature = format_temperature(low if low is not None else _number(row.get("temperature_c")))

        wind_speed = _number(row.get("wind_speed_ms"))
        wind_gust = _number(row.get("wind_gust_ms"))
        card_records.append({
            "date_or_time": date_or_time,
            "icon": _weather_icon(str(row.get("sky") or "")),
            "temperature": temperature,
            "sky": str(row.get("sky") or "—"),
            "wind_speed": f"{wind_speed:.0f}" if wind_speed is not None else "—",
            "wind_gust": f"{wind_gust:.0f}" if wind_gust is not None else "—",
            "wind_direction": str(row.get("wind_direction") or ""),
        })

    wind_values = [
        number for row in records
        if (number := _number(row.get("wind_speed_ms"))) is not None
    ]
    gust_values = [
        number for row in records
        if (number := _number(row.get("wind_gust_ms"))) is not None
    ]
    average_wind = sum(wind_values) / len(wind_values) if wind_values else None
    max_gust = max(gust_values) if gust_values else None

    if daily and first_low is not None and first_high is not None and first_low != first_high:
        first_temperature = f"{format_temperature(first_low)} … {format_temperature(first_high)}"
        temperature_is_range = True
    else:
        first_temperature = format_temperature(
            first_low if first_low is not None else _number(records[0].get("temperature_c"))
        )
        temperature_is_range = False

    if daily:
        first_date, last_date = _row_date(records[0]), _row_date(records[-1])
        if first_date and last_date:
            date_label = _format_date(first_date, long_month=True)
            if first_date != last_date:
                date_label += " — " + _format_date(last_date, long_month=True)
        else:
            date_label = ""
        count_label = f"{len(records)} дней прогноза"
        section_kicker = "ПО ДНЯМ"
        section_title = "Прогноз на каждый день"
        chart_title = "Дневная температура (середина диапазона)"
        source_label = "Прогноз по дням"
    else:
        timestamp = _number(records[0].get("timestamp"))
        if timestamp is not None:
            first_day = datetime.fromtimestamp(timestamp, MOSCOW)
            date_label = f"{WEEKDAYS_LONG[first_day.weekday()]}, {first_day.day} {MONTHS[first_day.month - 1]}"
        else:
            date_label = ""
        count_label = f"{len(records)} временных точек"
        section_kicker = "ПО ВРЕМЕНИ"
        section_title = "Изменение погоды"
        chart_title = "Температура воздуха"
        source_label = "Почасовой прогноз"

    return {
        "period": period,
        "label": str(forecast.get("label") or period),
        "daily": daily,
        "records": card_records,
        "condition": str(records[0].get("sky") or "Погодные условия"),
        "date_label": date_label,
        "first_temperature": first_temperature,
        "temperature_is_range": temperature_is_range,
        "minimum_temperature": format_temperature(min(lows)) if lows else "—°",
        "maximum_temperature": format_temperature(max(highs)) if highs else "—°",
        "temperature_range": (
            f"{format_temperature(min(lows))} … {format_temperature(max(highs))}"
            if lows and highs else "—° … —°"
        ),
        "average_wind": f"{average_wind:.1f} м/с" if average_wind is not None else "— м/с",
        "maximum_gust": f"{max_gust:.1f} м/с" if max_gust is not None else "— м/с",
        "wind_summary": f"Порывы до {max_gust:.1f} м/с" if max_gust is not None else "Порывы —",
        "count_label": count_label,
        "section_kicker": section_kicker,
        "section_title": section_title,
        "chart_title": chart_title,
        "source_label": source_label,
        "chart_svg": _chart_svg(records, daily),
        "temperature_css_class": "is-range" if temperature_is_range else "",
    }
