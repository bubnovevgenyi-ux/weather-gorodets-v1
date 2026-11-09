"""FastAPI-сервис погоды в Городце, JSON API и серверный HTML-интерфейс."""

import json
import logging
import os
import secrets
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from src.collector import HTML_BACKUP_DIR, WEATHER_JSON_PATH, collect_forecasts
from src.presentation import build_forecast_view

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "web"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
ENV_FILE = PROJECT_ROOT / ".env"
REFRESH_LOCK = threading.Lock()
MOSCOW = ZoneInfo("Europe/Moscow")
PERIODS = ("today", "tomorrow", "10_days", "2_weeks")
PERIOD_LABELS = (
    {"key": "today", "label": "Сегодня"},
    {"key": "tomorrow", "label": "Завтра"},
    {"key": "10_days", "label": "10 дней"},
    {"key": "2_weeks", "label": "2 недели"},
)
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _get_refresh_token() -> str | None:
    """Прочитать токен из окружения или локального .env; окружение имеет приоритет."""
    load_dotenv(dotenv_path=ENV_FILE, override=False)
    return os.getenv("WEATHER_API_REFRESH_TOKEN") or None


def _format_updated_at(value: Any) -> str:
    """Отобразить время получения данных в часовом поясе Городца."""
    if not value:
        return "Время обновления неизвестно"
    try:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=ZoneInfo("UTC"))
        return "Получено " + timestamp.astimezone(MOSCOW).strftime("%d.%m.%Y в %H:%M МСК")
    except (TypeError, ValueError, OverflowError):
        return "Данные прогноза"


def _read_forecast() -> dict[str, Any]:
    """Прочитать и проверить сохранённый JSON прогноза."""
    try:
        with WEATHER_JSON_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Прогноз ещё не загружен. При запуске сервера выполняется "
                "первичная загрузка; также доступно защищённое POST /api/v1/refresh."
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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """При первом старте автоматически получить прогноз, если локального кэша нет."""
    if not WEATHER_JSON_PATH.is_file():
        logger.info("Сохранённый прогноз не найден; выполняется первичная загрузка Gismeteo.")
        try:
            await run_in_threadpool(collect_forecasts, WEATHER_JSON_PATH)
        except Exception:
            # Ошибка источника не должна блокировать запуск веб-интерфейса и API.
            logger.exception("Не удалось выполнить первичную загрузку прогноза.")
    yield


app = FastAPI(
    title="Weather Gorodets API",
    version="2.0.0",
    description=(
        "Серверный HTML-интерфейс и JSON API почасового и дневного прогноза погоды "
        "в Городце. Данные собираются парсером Gismeteo и сохраняются локально."
    ),
    docs_url="/api/swagger",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request, period: str = "today") -> HTMLResponse:
    """Отрендерить выбранный период прогноза на сервере через Jinja2."""
    if period not in PERIODS:
        raise HTTPException(
            status_code=404,
            detail=f"Неизвестный период {period!r}. Допустимые значения: {', '.join(PERIODS)}.",
        )

    try:
        payload = _read_forecast()
    except HTTPException as exc:
        if exc.status_code != 503:
            raise
        payload = {"forecasts": {}}

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "periods": PERIOD_LABELS,
            "selected_period": period,
            "forecast": build_forecast_view(payload, period),
            "updated_label": _format_updated_at(payload.get("fetched_at_utc")),
        },
    )


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
        }

    return {
        "status": "ok",
        "forecast_available": True,
        "fetched_at_utc": payload.get("fetched_at_utc"),
        "available_periods": list(payload["forecasts"].keys()),
        "cached_html_pages": cached_pages,
        "refresh_enabled": bool(_get_refresh_token()),
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
        collect_forecasts(destination=WEATHER_JSON_PATH)
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


# Веб-ресурсы раздаются отдельно; корневой URL обслуживается шаблоном FastAPI/Jinja2.
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
