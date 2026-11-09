"""Необязательное подключение процесса FastAPI к удалённому отладчику PyCharm."""

import importlib
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
_TRUE_VALUES = {"1", "true", "yes", "on"}


def configure_pydevd(env_file: Path) -> bool:
    """Подключить PyDev debugger, если это явно включено через окружение.

    Функция вызывается при импорте api.py, то есть в процессе, который запускает
    Uvicorn. По умолчанию отладчик выключен и pydevd_pycharm не импортируется.
    """
    load_dotenv(dotenv_path=env_file, override=False)

    enabled = os.getenv("PYCHARM_DEBUG", "0").strip().lower() in _TRUE_VALUES
    if not enabled:
        return False

    host = os.getenv("PYCHARM_DEBUG_HOST", "localhost").strip() or "localhost"
    raw_port = os.getenv("PYCHARM_DEBUG_PORT", "5678").strip()
    suspend = os.getenv("PYCHARM_DEBUG_SUSPEND", "0").strip().lower() in _TRUE_VALUES

    try:
        port = int(raw_port)
    except ValueError as exc:
        raise RuntimeError(
            f"Некорректное значение PYCHARM_DEBUG_PORT: {raw_port!r}. "
            "Ожидается целое число от 1 до 65535."
        ) from exc

    if not 1 <= port <= 65535:
        raise RuntimeError("PYCHARM_DEBUG_PORT должен быть в диапазоне от 1 до 65535.")

    try:
        debugger = importlib.import_module("pydevd_pycharm")
    except ImportError as exc:
        raise RuntimeError(
            "Удалённая отладка включена (PYCHARM_DEBUG=1), но pydevd-pycharm не установлен. "
            "Установите зависимости командой: python -m pip install -r requirements-debug.txt. "
            "Версия pydevd-pycharm должна соответствовать сборке PyCharm."
        ) from exc

    logger.info("Подключение PyCharm Debug Server: %s:%s", host, port)
    debugger.settrace(
        host,
        port=port,
        stdout_to_server=True,
        stderr_to_server=True,
        suspend=suspend,
    )
    logger.info("Подключение к PyCharm Debug Server выполнено.")
    return True
