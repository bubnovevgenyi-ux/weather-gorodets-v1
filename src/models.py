from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HourlyWeather:
    """Погодные показатели на один часовой момент."""

    timestamp: int
    time: str
    sky: str
    temperature_c: float
    wind_speed_ms: float
    wind_gust_ms: float
    wind_direction: str | None


@dataclass(frozen=True, slots=True)
class DailyWeather:
    """Погодные показатели за календарный день."""

    timestamp: int
    date: str
    sky: str
    temperature_c: float | None
    temperature_min_c: float | None
    temperature_max_c: float | None
    wind_speed_ms: float
    wind_gust_ms: float
    wind_direction: str | None


# Unix timestamp (секунды UTC) — индекс записи прогноза.
WeatherByTimestamp = dict[int, HourlyWeather]
WeatherByDate = dict[int, DailyWeather]
