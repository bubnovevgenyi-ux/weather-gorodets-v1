"""Сохранение почасовых и дневных прогнозов в один JSON-файл."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import DailyWeather, HourlyWeather


def save_forecasts_json(
    forecasts: dict[str, dict[int, HourlyWeather | DailyWeather]],
    labels: dict[str, str],
    source_urls: dict[str, str],
    destination: Path = Path("data/weather.json"),
) -> Path:
    """Атомарно сохранить прогнозы; дневные и почасовые записи держать отдельно."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    periods = {}
    for period, forecast in forecasts.items():
        if period not in labels or period not in source_urls:
            raise ValueError(f"Для прогноза {period!r} отсутствует подпись или URL.")

        records = list(forecast.values())
        if not records:
            raise ValueError(f"Прогноз {period!r} не содержит записей.")

        if all(isinstance(record, DailyWeather) for record in records):
            collection_key = "days"
        elif all(isinstance(record, HourlyWeather) for record in records):
            collection_key = "hours"
        else:
            raise ValueError(f"Прогноз {period!r} смешивает дневные и почасовые записи.")

        periods[period] = {
            "label": labels[period],
            "source_url": source_urls[period],
            "resolution": "daily" if collection_key == "days" else "hourly",
            collection_key: {
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
