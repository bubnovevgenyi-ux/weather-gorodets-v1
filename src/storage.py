"""Сохранение прогнозов на сегодня и завтра в один JSON-файл."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import WeatherByTimestamp


def save_forecasts_json(
    forecasts: dict[str, WeatherByTimestamp],
    labels: dict[str, str],
    source_urls: dict[str, str],
    destination: Path = Path("data/weather.json"),
) -> Path:
    """Атомарно сохранить несколько прогнозов с отдельными метками периодов."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    periods = {}
    for period, forecast in forecasts.items():
        if period not in labels or period not in source_urls:
            raise ValueError(f"Для прогноза {period!r} отсутствует подпись или URL.")

        periods[period] = {
            "label": labels[period],
            "source_url": source_urls[period],
            "hours": {
                str(timestamp): asdict(record)
                for timestamp, record in forecast.items()
            },
        }

    payload = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "forecasts": periods,
    }

    temporary_file = destination.with_suffix(destination.suffix + ".tmp")
    temporary_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_file.replace(destination)
    return destination
