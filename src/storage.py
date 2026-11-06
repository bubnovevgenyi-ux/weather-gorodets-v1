"""Сохранение собранного прогноза на диск."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import WeatherByTimestamp


def save_forecast_json(
    forecast: WeatherByTimestamp,
    destination: Path = Path("data/weather.json"),
    source_url: str = "",
) -> Path:
    """Атомарно сохранить прогноз в JSON, индексированный timestamp."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_url": source_url,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "hours": {
            str(timestamp): asdict(record)
            for timestamp, record in forecast.items()
        },
    }
    temporary_file = destination.with_suffix(destination.suffix + ".tmp")
    temporary_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_file.replace(destination)
    return destination
