from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HourlyWeather:
    """Погодные показатели на один момент времени."""

    timestamp: int
    time: str
    sky: str
    temperature_c: float
    wind_speed_ms: float
    wind_gust_ms: float
    wind_direction: str | None
    icon_path: str | None
    icon_symbols: tuple[str, ...]


# Ключ — Unix timestamp (секунды UTC), значение — запись прогноза.
WeatherByTimestamp = dict[int, HourlyWeather]
