"""FastAPI-сервис погоды в Городце и API для веб-интерфейса."""

import json
import os
import secrets
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from src.collector import HTML_BACKUP_DIR, WEATHER_JSON_PATH, collect_forecasts

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "web"
ENV_FILE = PROJECT_ROOT / ".env"


def _get_refresh_token() -> str | None:
    """Прочитать токен из окружения или локального .env; окружение имеет приоритет."""
    load_dotenv(dotenv_path=ENV_FILE, override=False)
    return os.getenv("WEATHER_API_REFRESH_TOKEN") or None
REFRESH_LOCK = threading.Lock()
PERIODS = ("today", "tomorrow", "10_days", "2_weeks")

app = FastAPI(
    title="Weather Gorodets API",
    version="1.0.0",
    description=(
        "API почасового и дневного прогноза погоды в Городце. "
        "Данные собираются парсером Gismeteo и сохраняются локально."
    ),
    docs_url="/api/swagger",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)


def _read_forecast() -> dict[str, Any]:
    """Прочитать и проверить сохранённый JSON прогноза."""
    try:
        with WEATHER_JSON_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Прогноз ещё не загружен. Выполните python main.py "
                "или настройте защищённый POST /api/v1/refresh."
            ),
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Не удалось прочитать сохранённый прогноз: {exc}",
        ) from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("forecasts"), dict):
        raise HTTPException(
            status_code=503,
            detail="Файл прогноза имеет неверную структуру.",
        )
    return payload


@app.get("/api/v1/health", tags=["Сервис"], summary="Состояние сервиса")
def health() -> dict[str, Any]:
    """Проверить работоспособность API и наличие погодных данных."""
    cached_pages = [
        period
        for period in PERIODS
        if (HTML_BACKUP_DIR / f"{period}.html").is_file()
    ]

    try:
        payload = _read_forecast()
    except HTTPException:
        return {
            "status": "not_initialized",
            "forecast_available": False,
            "cached_html_pages": cached_pages,
        "refresh_enabled": bool(_get_refresh_token()),
            "refresh_enabled": bool(_get_refresh_token()),
        }

    return {
        "status": "ok",
        "forecast_available": True,
        "fetched_at_utc": payload.get("fetched_at_utc"),
        "available_periods": list(payload["forecasts"].keys()),
        "cached_html_pages": cached_pages,
    }


@app.get(
    "/api/v1/forecast",
    tags=["Прогноз"],
    summary="Полный прогноз погоды",
)
def get_forecast() -> dict[str, Any]:
    """Вернуть все сохранённые периоды прогноза."""
    return _read_forecast()


@app.get(
    "/api/v1/forecast/{period}",
    tags=["Прогноз"],
    summary="Прогноз на выбранный период",
)
def get_forecast_period(period: str) -> dict[str, Any]:
    """Вернуть один из периодов: today, tomorrow, 10_days или 2_weeks."""
    if period not in PERIODS:
        raise HTTPException(
            status_code=404,
            detail=f"Неизвестный период {period!r}. Допустимые значения: {', '.join(PERIODS)}.",
        )

    payload = _read_forecast()
    forecast = payload["forecasts"].get(period)
    if forecast is None:
        raise HTTPException(
            status_code=404,
            detail=f"Для периода {period!r} пока нет данных.",
        )

    return {
        "fetched_at_utc": payload.get("fetched_at_utc"),
        "period": period,
        **forecast,
    }


@app.post(
    "/api/v1/refresh",
    tags=["Обновление"],
    summary="Загрузить и разобрать свежий прогноз",
)
def refresh_forecast(
    x_refresh_token: str | None = Header(default=None, alias="X-Refresh-Token"),
) -> dict[str, Any]:
    """Обновить данные; доступ только при настроенном WEATHER_API_REFRESH_TOKEN."""
    expected_token = _get_refresh_token()
    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail=(
                "Обновление через API отключено: токен не найден. "
                "Создайте файл .env в корне проекта, задайте "
                "WEATHER_API_REFRESH_TOKEN=ваш_секретный_токен и перезапустите сервер."
            ),
        )
    if not x_refresh_token or not secrets.compare_digest(x_refresh_token, expected_token):
        raise HTTPException(status_code=401, detail="Неверный или отсутствующий X-Refresh-Token.")

    if not REFRESH_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Обновление прогноза уже выполняется.")

    try:
        collect_forecasts()
        return _read_forecast()
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Не удалось обновить прогноз из Gismeteo: {exc}",
        ) from exc
    finally:
        REFRESH_LOCK.release()


@app.get("/api-docs", include_in_schema=False)
@app.get("/api-docs/", include_in_schema=False)
def api_documentation() -> FileResponse:
    """Отдельная русскоязычная страница документации API."""
    return FileResponse(WEB_DIR / "api-docs.html")


# Веб-интерфейс размещён на том же origin, что и API. Поэтому CORS не нужен.
# Mount регистрируется после API-маршрутов, чтобы не перехватывать их.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
