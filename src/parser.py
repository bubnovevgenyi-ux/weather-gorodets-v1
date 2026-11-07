"""Извлечение почасового и дневного прогноза из погодного виджета Gismeteo."""
import re
from datetime import date as Date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

from .models import DailyWeather, HourlyWeather, WeatherByDate, WeatherByTimestamp

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
    local_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(FORECAST_TIMEZONE)
    return f"{local_time.hour}:{local_time.minute:02d}"


def _local_date(timestamp: int) -> str:
    return (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .astimezone(FORECAST_TIMEZONE)
        .date()
        .isoformat()
    )


def _widget(page_soup: BeautifulSoup) -> Tag:
    widget = page_soup.select_one(WIDGET_SELECTOR)
    if widget is None:
        raise ValueError(f"Не найден блок Gismeteo {WIDGET_SELECTOR}.")
    return widget


def _required_row(widget: Tag, selectors: tuple[str, ...], label: str) -> Tag:
    for selector in selectors:
        row = widget.select_one(selector)
        if row is not None:
            return row
    raise ValueError(f"В погодном блоке отсутствует ряд «{label}».")


def _row_cells(row: Tag, expected: int, label: str) -> list[Tag]:
    """Получить колонки ряда; разные версии виджета используют row-item или chart.value."""
    candidates = (
        row.select(":scope > .row-item"),
        row.select(".chart .values .value"),
        row.select(".values > .value"),
    )
    for cells in candidates:
        if len(cells) == expected:
            return cells
    details = [len(cells) for cells in candidates]
    raise ValueError(
        f"Не удалось сопоставить ряд «{label}» с {expected} датами. "
        f"Количество найденных ячеек: {details}."
    )


_RUSSIAN_MONTHS = {
    "янв": 1, "январь": 1, "января": 1,
    "фев": 2, "февраль": 2, "февраля": 2,
    "мар": 3, "март": 3, "марта": 3,
    "апр": 4, "апрель": 4, "апреля": 4,
    "май": 5, "мая": 5,
    "июн": 6, "июнь": 6, "июня": 6,
    "июл": 7, "июль": 7, "июля": 7,
    "авг": 8, "август": 8, "августа": 8,
    "сен": 9, "сент": 9, "сентябрь": 9, "сентября": 9,
    "окт": 10, "октябрь": 10, "октября": 10,
    "ноя": 11, "нояб": 11, "ноябрь": 11, "ноября": 11,
    "дек": 12, "декабрь": 12, "декабря": 12,
}


def _today_local_date() -> Date:
    """Текущая календарная дата по часовому поясу города прогноза."""
    return datetime.now(FORECAST_TIMEZONE).date()


def _date_from_cell(cell: Tag, index: int, previous_date: Date | None) -> Date:
    """Получить календарную дату из timestamp либо видимой подписи Gismeteo."""
    node = cell if cell.has_attr("timestamp") else cell.select_one("[timestamp]")
    raw_timestamp = node.get("timestamp") if node else cell.get("data-timestamp")
    if raw_timestamp is not None:
        try:
            return datetime.fromtimestamp(
                int(raw_timestamp), tz=timezone.utc
            ).astimezone(FORECAST_TIMEZONE).date()
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Для дневной точки №{index + 1} указан некорректный timestamp."
            ) from exc

    time_node = cell.select_one("time[datetime]")
    raw_datetime = time_node.get("datetime") if time_node else None
    if raw_datetime:
        try:
            parsed = datetime.fromisoformat(str(raw_datetime).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=FORECAST_TIMEZONE)
            return parsed.astimezone(FORECAST_TIMEZONE).date()
        except ValueError as exc:
            raise ValueError(
                f"Для дневной точки №{index + 1} указана некорректная дата."
            ) from exc

    date_node = cell.select_one(".date")
    raw_date = (date_node or cell).get_text(" ", strip=True).lower()
    match = re.search(r"(?P<day>\d{1,2})(?:\s+(?P<month>[а-яё]+)\.?)?", raw_date)
    if match is None:
        raise ValueError(
            f"Не удалось прочитать дату дневной точки №{index + 1}: {raw_date!r}."
        )

    day = int(match.group("day"))
    month_text = (match.group("month") or "").rstrip(".")
    month = _RUSSIAN_MONTHS.get(month_text) if month_text else None
    if month_text and month is None:
        raise ValueError(
            f"Неизвестное название месяца в дате дневной точки №{index + 1}: "
            f"{month_text!r}."
        )

    if previous_date is not None:
        expected_date = previous_date + timedelta(days=1)
        if month is None:
            candidate = expected_date
        else:
            try:
                candidate = Date(expected_date.year, month, day)
                if candidate < expected_date:
                    candidate = Date(expected_date.year + 1, month, day)
            except ValueError as exc:
                raise ValueError(
                    f"Некорректная дата дневной точки №{index + 1}: {raw_date!r}."
                ) from exc

        if candidate != expected_date:
            raise ValueError(
                f"Нарушена последовательность дат прогноза: ожидалась "
                f"{expected_date.isoformat()}, получено {candidate.isoformat()}."
            )
        return candidate

    if month is not None:
        today = _today_local_date()
        candidates = []
        for year in (today.year - 1, today.year, today.year + 1):
            try:
                candidates.append(Date(year, month, day))
            except ValueError:
                continue
        if not candidates:
            raise ValueError(f"Некорректная первая дата прогноза: {raw_date!r}.")
        return min(candidates, key=lambda candidate: abs((candidate - today).days))

    today = _today_local_date()
    nearby_dates = [
        today + timedelta(days=offset)
        for offset in range(-14, 15)
        if (today + timedelta(days=offset)).day == day
    ]
    if not nearby_dates:
        raise ValueError(
            f"Не удалось определить месяц первой даты прогноза: {raw_date!r}."
        )
    return min(nearby_dates, key=lambda candidate: abs((candidate - today).days))


def _temperature_groups(row: Tag, day_count: int) -> list[list[float]]:
    """Вернуть температурные значения по дням; в колонке может быть одна или две температуры."""
    direct_cells = row.select(":scope > .row-item")
    chart_cells = row.select(".chart .values .value")
    chart_cells_alt = row.select(".values > .value")

    for candidate in (direct_cells, chart_cells, chart_cells_alt):
        if len(candidate) != day_count:
            continue
        groups = []
        candidate_is_complete = True
        for cell in candidate:
            value_tags = cell.select("temperature-value[value]")
            if not value_tags and cell.name == "temperature-value":
                value_tags = [cell]
            if not value_tags:
                value_tags = [
                    tag for tag in cell.select(".value")
                    if tag.get("value") is not None
                ]
            if not value_tags:
                candidate_is_complete = False
                break
            groups.append([_number_from_tag(tag, "температура") for tag in value_tags])
        if candidate_is_complete:
            return groups

    value_tags = row.select("temperature-value[value]")
    if not value_tags:
        raise ValueError("В дневном ряду температуры не найдены элементы temperature-value.")

    if len(value_tags) == day_count:
        return [[_number_from_tag(tag, "температура")] for tag in value_tags]
    if len(value_tags) == day_count * 2:
        return [
            [
                _number_from_tag(value_tags[index * 2], "минимальная температура"),
                _number_from_tag(value_tags[index * 2 + 1], "максимальная температура"),
            ]
            for index in range(day_count)
        ]

    raise ValueError(
        f"Число температурных значений ({len(value_tags)}) не соответствует "
        f"{day_count} дням."
    )


def _sky_description(cell: Tag) -> str:
    return str(
        cell.get("data-tooltip")
        or cell.get("title")
        or cell.get("aria-label")
        or ""
    ).strip()


def _wind_values(cell: Tag, index: int) -> tuple[float, float, str | None]:
    speed_tag = cell.select_one(".wind-speed speed-value, .wind-speed [value]")
    gust_tag = cell.select_one(".wind-gust speed-value, .wind-gust [value]")
    if speed_tag is None:
        raise ValueError(f"Не найдена скорость ветра для дня №{index + 1}.")
    if gust_tag is None:
        # Допускаем fallback на второй speed-value, если классы обёрток изменились.
        candidates = cell.select("speed-value[value]")
        if len(candidates) >= 2:
            speed_tag, gust_tag = candidates[0], candidates[1]
    if gust_tag is None:
        raise ValueError(f"Не найдены порывы ветра для дня №{index + 1}.")
    direction_tag = cell.select_one(".wind-direction")
    direction = direction_tag.get_text(" ", strip=True) if direction_tag else None
    return (
        _number_from_tag(speed_tag, "скорость ветра"),
        _number_from_tag(gust_tag, "порывы ветра"),
        direction,
    )


def parse_weather_widget(page_soup: BeautifulSoup) -> WeatherByTimestamp:
    """Распарсить почасовой виджет для страниц «сегодня» и «завтра»."""
    widget = _widget(page_soup)
    time_row = _required_row(widget, (".widget-row-datetime-time",), "время")
    sky_row = _required_row(widget, ('[data-row="icon-tooltip"]',), "состояние неба")
    temp_row = _required_row(widget, ('[data-row="temperature-air"]',), "температура")
    wind_row = _required_row(widget, ('[data-row="wind"]',), "ветер")

    time_cells = time_row.select(".row-item")
    sky_cells = _row_cells(sky_row, len(time_cells), "состояние неба")
    temp_cells = temp_row.select(".chart .values .value")
    if not temp_cells:
        temp_cells = temp_row.select(".values > .value")
    wind_cells = _row_cells(wind_row, len(time_cells), "ветер")

    counts = {
        "время": len(time_cells),
        "небо": len(sky_cells),
        "температура": len(temp_cells),
        "ветер": len(wind_cells),
    }
    expected = counts["время"]
    if expected == 0 or any(count != expected for count in counts.values()):
        raise ValueError(f"Число элементов почасовых рядов не совпадает: {counts}")

    forecast: WeatherByTimestamp = {}
    for index, time_cell in enumerate(time_cells):
        time_tag = time_cell.select_one("time-value[timestamp], [timestamp]")
        if time_tag is None:
            raise ValueError(f"Для почасовой точки №{index + 1} отсутствует timestamp.")
        try:
            timestamp = int(time_tag["timestamp"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Некорректный timestamp для точки №{index + 1}.") from exc
        if timestamp in forecast:
            raise ValueError(f"Повторяющийся timestamp: {timestamp}")

        wind_speed, wind_gust, wind_direction = _wind_values(wind_cells[index], index)
        forecast[timestamp] = HourlyWeather(
            timestamp=timestamp,
            time=_format_forecast_time(timestamp),
            sky=_sky_description(sky_cells[index]),
            temperature_c=_number_from_tag(
                temp_cells[index].select_one("temperature-value") or temp_cells[index],
                "температура",
            ),
            wind_speed_ms=wind_speed,
            wind_gust_ms=wind_gust,
            wind_direction=wind_direction,
        )
    return forecast


def parse_daily_weather_widget(
    page_soup: BeautifulSoup,
    expected_days: int,
) -> WeatherByDate:
    """Распарсить дневной прогноз; expected_days задаёт 10 или 14 дней."""
    if expected_days not in (10, 14):
        raise ValueError("Для дневного прогноза допустимо expected_days=10 или expected_days=14.")

    widget = _widget(page_soup)
    date_row = _required_row(
        widget,
        (".widget-row-date", ".widget-row-datetime-date", ".widget-row-datetime-time", '[data-row="date"]'),
        "даты прогноза",
    )
    date_cells = date_row.select(":scope > .row-item")
    if len(date_cells) != expected_days:
        # У некоторых версий виджета дата располагается в chart/values.
        alternatives = date_row.select(".chart .values .value") or date_row.select(".values > .value")
        if len(alternatives) == expected_days:
            date_cells = alternatives
    if len(date_cells) != expected_days:
        raise ValueError(
            f"Ожидалось {expected_days} дневных дат, найдено {len(date_cells)}."
        )

    sky_row = _required_row(widget, ('[data-row="icon-tooltip"]',), "состояние неба")
    temp_row = _required_row(widget, ('[data-row="temperature-air"]',), "температура")
    wind_row = _required_row(widget, ('[data-row="wind"]',), "ветер")

    sky_cells = _row_cells(sky_row, expected_days, "состояние неба")
    wind_cells = _row_cells(wind_row, expected_days, "ветер")
    temp_groups = _temperature_groups(temp_row, expected_days)

    forecast: WeatherByDate = {}
    previous_date: Date | None = None
    for index, date_cell in enumerate(date_cells):
        forecast_date = _date_from_cell(date_cell, index, previous_date)
        previous_date = forecast_date
        timestamp = int(
            datetime(
                forecast_date.year,
                forecast_date.month,
                forecast_date.day,
                tzinfo=FORECAST_TIMEZONE,
            ).timestamp()
        )
        if timestamp in forecast:
            raise ValueError(f"Повторяющаяся дата прогноза: {_local_date(timestamp)}")

        temperatures = temp_groups[index]
        if len(temperatures) == 1:
            temperature_c = temperatures[0]
            temperature_min_c = None
            temperature_max_c = None
        else:
            temperature_c = None
            temperature_min_c = min(temperatures)
            temperature_max_c = max(temperatures)

        wind_speed, wind_gust, wind_direction = _wind_values(wind_cells[index], index)
        forecast[timestamp] = DailyWeather(
            timestamp=timestamp,
            date=_local_date(timestamp),
            sky=_sky_description(sky_cells[index]),
            temperature_c=temperature_c,
            temperature_min_c=temperature_min_c,
            temperature_max_c=temperature_max_c,
            wind_speed_ms=wind_speed,
            wind_gust_ms=wind_gust,
            wind_direction=wind_direction,
        )

    return forecast
