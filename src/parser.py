"""Извлечение погодных показателей из виджета Gismeteo."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from .models import HourlyWeather, WeatherByTimestamp

WIDGET_SELECTOR = '[data-widget="weather-parameters"]'


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


def _extract_icon_layers(cell: Tag) -> list[tuple[str, str, str]]:
    layers = []
    for role in ("top-layer", "bottom-layer"):
        svg = cell.select_one(f"svg.{role}")
        if svg is None:
            continue
        use = svg.find("use")
        if use is None:
            continue
        href = use.get("href") or use.get("xlink:href")
        if href and str(href).startswith("#"):
            default_viewbox = "0 0 55 8" if role == "bottom-layer" else "0 0 55 38"
            viewbox = svg.get("viewbox") or svg.get("viewBox") or default_viewbox
            layers.append((role, str(viewbox), str(href)[1:]))
    return layers


def _referenced_ids(element: Tag) -> set[str]:
    refs: set[str] = set()
    for node in [element, *element.find_all(True)]:
        for attr in ("href", "xlink:href"):
            value = node.get(attr)
            if isinstance(value, str) and value.startswith("#"):
                refs.add(value[1:])
        for value in node.attrs.values():
            values = value if isinstance(value, list) else (value,)
            for item in values:
                if isinstance(item, str):
                    refs.update(re.findall(r"url\(#([^)]+)\)", item))
    return refs


def _collect_svg_definitions(soup: BeautifulSoup, root_ids: set[str]) -> list[str] | None:
    pending = list(root_ids)
    definitions: dict[str, Tag] = {}
    while pending:
        symbol_id = pending.pop()
        if symbol_id in definitions:
            continue
        definition = soup.find(id=symbol_id)
        if not isinstance(definition, Tag):
            return None
        definitions[symbol_id] = definition
        pending.extend(_referenced_ids(definition) - definitions.keys())

    serialized = [str(definition) for definition in definitions.values()]
    # lxml's HTML parser normalizes SVG's case-sensitive attribute names.
    svg_attribute_names = {
        "viewbox": "viewBox",
        "preserveaspectratio": "preserveAspectRatio",
        "gradientunits": "gradientUnits",
        "gradienttransform": "gradientTransform",
        "spreadmethod": "spreadMethod",
        "patternunits": "patternUnits",
        "patterncontentunits": "patternContentUnits",
        "patterntransform": "patternTransform",
        "clippathunits": "clipPathUnits",
        "maskunits": "maskUnits",
        "maskcontentunits": "maskContentUnits",
        "markerunits": "markerUnits",
        "markerwidth": "markerWidth",
        "markerheight": "markerHeight",
        "refx": "refX",
        "refy": "refY",
    }
    for index, markup in enumerate(serialized):
        for html_name, svg_name in svg_attribute_names.items():
            markup = re.sub(rf"\b{html_name}=", f"{svg_name}=", markup)
        serialized[index] = markup
    return serialized


def _save_svg_icon(
    soup: BeautifulSoup,
    cell: Tag,
    icon_dir: Path,
) -> tuple[str | None, tuple[str, ...]]:
    layers = _extract_icon_layers(cell)
    symbol_ids = tuple(layer[2] for layer in layers)
    if not layers:
        return None, symbol_ids

    definitions = _collect_svg_definitions(soup, set(symbol_ids))
    if definitions is None:
        # Без исходных SVG-символов файл содержал бы неразрешённые ссылки.
        return None, symbol_ids

    key = "|".join(f"{role}:{viewbox}:{symbol}" for role, viewbox, symbol in layers)
    filename = "weather_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12] + ".svg"
    icon_dir.mkdir(parents=True, exist_ok=True)
    icon_file = icon_dir / filename

    if not icon_file.exists():
        nested = []
        for role, viewbox, symbol in layers:
            y, height = (30, 8) if role == "bottom-layer" else (0, 38)
            nested.append(
                f'<svg x="0" y="{y}" width="55" height="{height}" viewBox="{viewbox}">'
                f'<use href="#{symbol}" /></svg>'
            )
        icon_file.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 55 38">'
            f'<defs>{"".join(definitions)}</defs>{"".join(nested)}</svg>',
            encoding="utf-8",
        )
    return icon_file.as_posix(), symbol_ids


def parse_weather_widget(
    page_soup: BeautifulSoup,
    icon_dir: Path = Path("assets/weather_icons"),
) -> WeatherByTimestamp:
    """Распарсить виджет, сопоставляя строки по индексу временной точки.

    Результат — dict с Unix timestamp в качестве ключа: средний O(1) доступ.
    """
    widget = page_soup.select_one(WIDGET_SELECTOR)
    if widget is None:
        raise ValueError(f"Не найден блок Gismeteo {WIDGET_SELECTOR}.")

    time_row = widget.select_one(".widget-row-datetime-time")
    icon_row = widget.select_one('[data-row="icon-tooltip"]')
    temp_row = widget.select_one('[data-row="temperature-air"]')
    wind_row = widget.select_one('[data-row="wind"]')
    if any(row is None for row in (time_row, icon_row, temp_row, wind_row)):
        raise ValueError("В погодном блоке отсутствует один из обязательных рядов.")

    time_cells = time_row.select(".row-item")
    icon_cells = icon_row.select(":scope > .row-item")
    temp_cells = temp_row.select(".chart .values .value")
    wind_cells = wind_row.select(":scope > .row-item")
    counts = {
        "время": len(time_cells),
        "небо": len(icon_cells),
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
        timestamp = int(time_tag["timestamp"])
        if timestamp in forecast:
            raise ValueError(f"Повторяющийся timestamp: {timestamp}")

        icon_cell = icon_cells[index]
        icon_path, icon_symbols = _save_svg_icon(page_soup, icon_cell, icon_dir)
        direction_tag = wind_cells[index].select_one(".wind-direction")

        forecast[timestamp] = HourlyWeather(
            timestamp=timestamp,
            time=time_tag.get_text(strip=True),
            sky=str(icon_cell.get("data-tooltip", "")).strip(),
            temperature_c=_number_from_tag(
                temp_cells[index].select_one("temperature-value"), "температура"
            ),
            wind_speed_ms=_number_from_tag(
                wind_cells[index].select_one(".wind-speed speed-value"), "скорость ветра"
            ),
            wind_gust_ms=_number_from_tag(
                wind_cells[index].select_one(".wind-gust speed-value"), "порывы ветра"
            ),
            wind_direction=direction_tag.get_text(" ", strip=True) if direction_tag else None,
            icon_path=icon_path,
            icon_symbols=icon_symbols,
        )
    return forecast
