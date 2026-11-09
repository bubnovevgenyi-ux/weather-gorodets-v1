"""Утилиты для генерации JPEG-изображений прогноза погоды."""

import math
import os
import sys
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


MOSCOW = ZoneInfo("Europe/Moscow")
PERIODS = ("today", "tomorrow", "10_days", "2_weeks")
PERIOD_TITLES = {
    "today": "ПОГОДА СЕГОДНЯ",
    "tomorrow": "ПОГОДА ЗАВТРА",
    "10_days": "ПРОГНОЗ НА 10 ДНЕЙ",
    "2_weeks": "ПРОГНОЗ НА 14 ДНЕЙ",
}
MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
BACKGROUND = "#EFF5FB"
NAVY = "#17324D"
MUTED = "#71869A"
BLUE = "#1678BC"
WHITE = "#FFFFFF"
LINE = "#E3ECF4"
WARM = "#F2A84A"

def _as_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _temperature(value: float | None) -> str:
    if value is None:
        return "—°"
    rounded = int(value) if value.is_integer() else round(value, 1)
    return f"{'+' if value > 0 else ''}{rounded}°"


def _temperature_range(row: dict[str, Any]) -> tuple[float | None, float | None]:
    current = _as_number(row.get("temperature_c"))
    low = _as_number(row.get("temperature_min_c"))
    high = _as_number(row.get("temperature_max_c"))
    return current if low is None else low, current if high is None else high


def _record_date(row: dict[str, Any]) -> date | None:
    if row.get("date"):
        try:
            return date.fromisoformat(str(row["date"]))
        except ValueError:
            pass
    timestamp = _as_number(row.get("timestamp"))
    if timestamp is not None:
        try:
            return datetime.fromtimestamp(timestamp, MOSCOW).date()
        except (OverflowError, OSError, ValueError):
            pass
    return None


def _font_candidates(bold: bool, explicit: Path | None) -> list[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit)
    if os.getenv("WEATHER_FONT"):
        candidates.append(Path(os.environ["WEATHER_FONT"]))
    if os.name == "nt":
        candidates.extend([
            Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        ])
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        ])
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates.extend([
        Path("/usr/share/fonts/truetype/dejavu") / name,
        Path("/usr/share/fonts/dejavu") / name,
        Path("/usr/share/fonts/truetype/liberation2") / ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation") / ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"),
    ])
    return candidates


def _load_font(size: int, bold: bool = False, explicit: Path | None = None) -> ImageFont.FreeTypeFont:
    for candidate in _font_candidates(bold, explicit):
        if candidate.is_file():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except OSError:
                continue
    raise RuntimeError(
        "Не найден TrueType-шрифт с поддержкой кириллицы. "
        "Установите DejaVu Sans или передайте путь через font_path / WEATHER_FONT."
    )


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    value = str(text or "—")
    if draw.textbbox((0, 0), value, font=font)[2] <= max_width:
        return value
    while value and draw.textbbox((0, 0), value + "…", font=font)[2] > max_width:
        value = value[:-1]
    return value.rstrip() + "…"


def _draw_icon(draw: ImageDraw.ImageDraw, center: tuple[int, int], description: str, size: int = 60) -> None:
    """Draw weather pictograms with Pillow primitives; no emoji font is required."""
    x, y = center
    phrase = (description or "").casefold()
    sunny = "ясно" in phrase or "солнеч" in phrase
    rain = "дожд" in phrase or "морос" in phrase
    snow = "снег" in phrase
    storm = "гроз" in phrase
    partly = "перемен" in phrase

    if sunny or partly:
        sx = x + (size // 5 if partly else 0)
        sy = y - size // 7
        radius = size // 4
        for angle in range(0, 360, 45):
            radians = math.radians(angle)
            start = (sx + math.cos(radians) * (radius + 5), sy + math.sin(radians) * (radius + 5))
            end = (sx + math.cos(radians) * (radius + 13), sy + math.sin(radians) * (radius + 13))
            draw.line((start, end), fill=WARM, width=4)
        draw.ellipse((sx - radius, sy - radius, sx + radius, sy + radius), fill="#F7BD55")

    if not sunny:
        cloud_color = "#8CB7D5" if not (rain or snow or storm) else "#789EBB"
        cy = y + size // 8
        radius = size // 4
        draw.ellipse((x - size // 2, cy - radius // 2, x, cy + radius * 2), fill=cloud_color)
        draw.ellipse((x - radius // 2, cy - radius, x + radius + 4, cy + radius + 4), fill=cloud_color)
        draw.ellipse((x + 2, cy - radius // 2, x + size // 2, cy + radius * 2), fill=cloud_color)
        draw.rounded_rectangle((x - size // 2 + 5, cy + radius // 2, x + size // 2 - 3, cy + radius * 2), radius=10, fill=cloud_color)

    if rain:
        for offset in (-18, 0, 18):
            draw.line((x + offset, y + size // 2, x + offset - 7, y + size // 2 + 15), fill="#42A5D5", width=4)
    elif snow:
        for offset in (-15, 8, 25):
            yy = y + size // 2 + 8
            draw.line((x + offset - 5, yy, x + offset + 5, yy + 10), fill="#55A9D6", width=3)
            draw.line((x + offset + 5, yy, x + offset - 5, yy + 10), fill="#55A9D6", width=3)
    elif storm:
        draw.polygon([(x + 4, y + 12), (x - 8, y + 34), (x + 2, y + 34), (x - 3, y + 53), (x + 16, y + 27), (x + 6, y + 27)], fill=WARM)


def _background(width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    top, bottom = (224, 241, 252), (239, 245, 251)
    gradient_height = min(420, height)
    for y in range(gradient_height):
        ratio = y / max(1, gradient_height - 1)
        color = tuple(round(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    return image


def _header(
    image: Image.Image,
    period: str,
    payload: dict[str, Any],
    records: list[dict[str, Any]],
    fonts: dict[str, ImageFont.ImageFont],
) -> None:
    draw = ImageDraw.Draw(image)
    width, margin = image.width, 64
    draw.rounded_rectangle((margin, 48, width - margin, 168), radius=30, fill=NAVY)
    draw.text((margin + 34, 68), "ГОРОДЕЦ", font=fonts["city"], fill=WHITE)
    draw.text((margin + 36, 132), "НИЖЕГОРОДСКАЯ ОБЛАСТЬ", font=fonts["small_bold"], fill="#B9D6EA")
    draw.text((margin, 202), PERIOD_TITLES[period], font=fonts["title"], fill=NAVY)

    dates = [value for row in records if (value := _record_date(row)) is not None]
    if dates:
        date_label = f"{dates[0].day} {MONTHS[dates[0].month - 1]}"
        if dates[-1] != dates[0]:
            date_label += f" — {dates[-1].day} {MONTHS[dates[-1].month - 1]}"
    else:
        date_label = "Прогноз Gismeteo"
    draw.text((margin, 268), date_label, font=fonts["subtitle"], fill=MUTED)

    updated = "Обновлено: —"
    if payload.get("fetched_at_utc"):
        try:
            moment = datetime.fromisoformat(str(payload["fetched_at_utc"]).replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=ZoneInfo("UTC"))
            updated = "Обновлено " + moment.astimezone(MOSCOW).strftime("%d.%m, %H:%M")
        except (TypeError, ValueError, OverflowError):
            pass
    text_width = draw.textbbox((0, 0), updated, font=fonts["small"])[2]
    draw.text((width - margin - text_width, 279), updated, font=fonts["small"], fill=MUTED)


def _summary_card(
    draw: ImageDraw.ImageDraw,
    y: int,
    width: int,
    first: dict[str, Any],
    daily: bool,
    fonts: dict[str, ImageFont.ImageFont],
    records: list[dict[str, Any]],
) -> None:
    margin = 64
    draw.rounded_rectangle((margin, y, width - margin, y + 170), radius=26, fill=WHITE, outline=LINE, width=2)
    description = str(first.get("sky") or "Погодные условия")
    _draw_icon(draw, (margin + 88, y + 80), description, 72)
    draw.text((margin + 160, y + 28), _fit_text(draw, description, fonts["card_title"], 440), font=fonts["card_title"], fill=NAVY)

    low, high = _temperature_range(first)
    if daily and low is not None and high is not None and low != high:
        primary = f"{_temperature(low)} / {_temperature(high)}"
    else:
        primary = _temperature(low if low is not None else _as_number(first.get("temperature_c")))
    draw.text((margin + 160, y + 83), primary, font=fonts["hero_temp"], fill=BLUE)

    winds = [number for row in records if (number := _as_number(row.get("wind_speed_ms"))) is not None]
    gusts = [number for row in records if (number := _as_number(row.get("wind_gust_ms"))) is not None]
    wind_label = f"Ветер {sum(winds) / len(winds):.1f} м/с" if winds else "Ветер —"
    if gusts:
        wind_label += f"  •  порывы до {max(gusts):.0f} м/с"
    draw.text((margin + 164, y + 132), wind_label, font=fonts["small"], fill=MUTED)


def _draw_daily(image: Image.Image, records: list[dict[str, Any]], fonts: dict[str, ImageFont.ImageFont]) -> None:
    draw = ImageDraw.Draw(image)
    width, margin = image.width, 64
    y, row_height = 520, 94
    draw.text((margin + 12, y), "ДАТА", font=fonts["small_bold"], fill=MUTED)
    draw.text((margin + 245, y), "ПОГОДА", font=fonts["small_bold"], fill=MUTED)
    draw.text((margin + 650, y), "ТЕМП.", font=fonts["small_bold"], fill=MUTED)
    draw.text((width - margin - 145, y), "ВЕТЕР", font=fonts["small_bold"], fill=MUTED)
    y += 44

    for index, row in enumerate(records):
        draw.rounded_rectangle(
            (margin, y, width - margin, y + row_height - 8),
            radius=19,
            fill=WHITE if index % 2 == 0 else "#F8FBFE",
            outline=LINE,
            width=1,
        )
        day = _record_date(row)
        date_label = f"{WEEKDAYS[day.weekday()]}, {day.day:02d}.{day.month:02d}" if day else "—"
        draw.text((margin + 18, y + 24), date_label, font=fonts["row_bold"], fill=NAVY)

        description = str(row.get("sky") or "—")
        _draw_icon(draw, (margin + 282, y + 39), description, 46)
        draw.text((margin + 320, y + 27), _fit_text(draw, description, fonts["row"], 285), font=fonts["row"], fill=MUTED)

        low, high = _temperature_range(row)
        temp_text = (
            f"{_temperature(low)} / {_temperature(high)}"
            if low is not None and high is not None and low != high
            else _temperature(low if low is not None else high)
        )
        draw.text((margin + 650, y + 24), temp_text, font=fonts["row_bold"], fill=BLUE)

        wind = _as_number(row.get("wind_speed_ms"))
        gust = _as_number(row.get("wind_gust_ms"))
        wind_text = f"{wind:.0f}" if wind is not None else "—"
        draw.text((width - margin - 140, y + 17), f"{wind_text} м/с", font=fonts["row_bold"], fill=NAVY)
        draw.text((width - margin - 140, y + 52), f"порывы {gust:.0f}" if gust is not None else "порывы —", font=fonts["tiny"], fill=MUTED)
        y += row_height


def _draw_hourly(image: Image.Image, records: list[dict[str, Any]], fonts: dict[str, ImageFont.ImageFont]) -> None:
    draw = ImageDraw.Draw(image)
    width, margin = image.width, 64
    columns, gap = 3, 18
    card_width = (width - 2 * margin - (columns - 1) * gap) // columns
    card_height, top = 270, 530

    for index, row in enumerate(records):
        col, line = index % columns, index // columns
        x = margin + col * (card_width + gap)
        y = top + line * (card_height + gap)
        draw.rounded_rectangle((x, y, x + card_width, y + card_height), radius=24, fill=WHITE, outline=LINE, width=2)
        draw.text((x + 22, y + 18), str(row.get("time") or "—"), font=fonts["row_bold"], fill=NAVY)
        description = str(row.get("sky") or "—")
        _draw_icon(draw, (x + card_width // 2, y + 94), description, 68)

        temp = _temperature(_as_number(row.get("temperature_c")))
        temp_width = draw.textbbox((0, 0), temp, font=fonts["hero_temp"])[2]
        draw.text((x + (card_width - temp_width) // 2, y + 151), temp, font=fonts["hero_temp"], fill=BLUE)
        sky = _fit_text(draw, description, fonts["tiny"], card_width - 38)
        sky_width = draw.textbbox((0, 0), sky, font=fonts["tiny"])[2]
        draw.text((x + (card_width - sky_width) // 2, y + 204), sky, font=fonts["tiny"], fill=MUTED)

        wind = _as_number(row.get("wind_speed_ms"))
        gust = _as_number(row.get("wind_gust_ms"))
        wind_text = f"Ветер {wind:.0f} м/с" if wind is not None else "Ветер —"
        if gust is not None:
            wind_text += f" · порывы {gust:.0f}"
        draw.text((x + 22, y + card_height - 31), _fit_text(draw, wind_text, fonts["tiny"], card_width - 44), font=fonts["tiny"], fill=MUTED)


def render_period(
    payload: dict[str, Any],
    period: str,
    font_path: Path | None = None,
) -> bytes:
    """Render a forecast period into a compressed, phone-friendly JPEG."""
    if period not in PERIODS:
        raise ValueError(f"Неизвестный период: {period}")
    forecast = (payload.get("forecasts") or {}).get(period)
    if not isinstance(forecast, dict):
        raise ValueError(f"В JSON нет прогноза для периода {period!r}")

    daily = forecast.get("resolution") == "daily"
    rows_key = "days" if daily else "hours"
    source_rows = forecast.get(rows_key) or {}
    if not isinstance(source_rows, dict):
        raise ValueError(f"У прогноза {period!r} неверная структура {rows_key!r}")
    records = sorted(
        (row for row in source_rows.values() if isinstance(row, dict)),
        key=lambda row: _as_number(row.get("timestamp")) or 0.0,
    )
    if not records:
        raise ValueError(f"Для периода {period!r} нет погодных записей")

    fonts = {
        "city": _load_font(48, True, font_path),
        "title": _load_font(42, True, font_path),
        "subtitle": _load_font(29, False, font_path),
        "card_title": _load_font(31, True, font_path),
        "hero_temp": _load_font(43, True, font_path),
        "row": _load_font(25, False, font_path),
        "row_bold": _load_font(27, True, font_path),
        "small": _load_font(21, False, font_path),
        "small_bold": _load_font(18, True, font_path),
        "tiny": _load_font(19, False, font_path),
    }

    if daily:
        height = 330 + 170 + 20 + 44 + len(records) * 94 + 110
    else:
        row_count = math.ceil(len(records) / 3)
        height = 530 + row_count * 270 + max(0, row_count - 1) * 18 + 120
    width = 1080
    image = _background(width, height)
    _header(image, period, payload, records, fonts)
    _summary_card(ImageDraw.Draw(image), 330, width, records[0], daily, fonts, records)

    if daily:
        _draw_daily(image, records, fonts)
    else:
        _draw_hourly(image, records, fonts)

    draw = ImageDraw.Draw(image)
    footer_y = height - 78
    draw.line((64, footer_y - 20, width - 64, footer_y - 20), fill=LINE, width=2)
    draw.text((64, footer_y), "ПОГОДА В ГОРОДЦЕ", font=fonts["small_bold"], fill=BLUE)
    footer = "Источник: Gismeteo"
    footer_width = draw.textbbox((0, 0), footer, font=fonts["small"])[2]
    draw.text((width - 64 - footer_width, footer_y), footer, font=fonts["small"], fill=MUTED)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True, progressive=True)
    return buffer.getvalue()
