# weather-gorodets-v1

Веб-сервис прогноза погоды в Городце. Стек: Python 3.12, FastAPI, Requests, BeautifulSoup, lxml и HTML/CSS/JavaScript. Данные загружаются парсером Gismeteo, выдаются через JSON API и отображаются в веб-интерфейсе.

## Возможности

- Почасовой прогноз на сегодня и завтра.
- Дневной прогноз на 10 дней и 2 недели.
- Веб-интерфейс с вкладками, карточками прогноза и графиком температуры.
- HTTP API с JSON-ответами и проверкой состояния сервиса.
- Отдельная русскоязычная страница документации API.
- Интерактивная документация Swagger UI и схема OpenAPI.
- Сохранение HTML-страниц Gismeteo в `data/html_backup/` и использование последней копии при сетевой ошибке.

## Страницы прогноза Gismeteo

| Раздел | URL | Данные |
|---|---|---|
| `today` — сегодня | https://www.gismeteo.ru/weather-gorodets-4334/ | Почасовой прогноз |
| `tomorrow` — завтра | https://www.gismeteo.ru/weather-gorodets-4334/tomorrow/ | Почасовой прогноз |
| `10_days` — 10 дней | https://www.gismeteo.ru/weather-gorodets-4334/10-days/ | 10 дневных записей |
| `2_weeks` — 2 недели | https://www.gismeteo.ru/weather-gorodets-4334/2-weeks/ | 14 дневных записей |

## Установка и запуск (Windows PowerShell)

~~~powershell
py -3.12 --version
git clone https://github.com/bubnovevgenyi-ux/weather-gorodets-v1.git
cd weather-gorodets-v1

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Первичная загрузка прогноза и создание data/weather.json
python main.py

# Запуск API и веб-интерфейса
python -m uvicorn api:app --host 127.0.0.1 --port 8000
~~~

После запуска откройте:

- Веб-интерфейс: http://127.0.0.1:8000/
- Документация API: http://127.0.0.1:8000/api-docs
- Swagger UI: http://127.0.0.1:8000/api/swagger
- OpenAPI JSON: http://127.0.0.1:8000/api/openapi.json

Для уже склонированного проекта получите изменения командой `git pull origin main`.

## HTTP API

Базовый префикс: `/api/v1`.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/api/v1/health` | Статус сервиса, наличие данных и HTML-копий |
| `GET` | `/api/v1/forecast` | Все четыре периода прогноза |
| `GET` | `/api/v1/forecast/{period}` | Один период: `today`, `tomorrow`, `10_days`, `2_weeks` |
| `POST` | `/api/v1/refresh` | Повторная загрузка и разбор страниц Gismeteo |

Примеры:

~~~powershell
# Полный прогноз
curl.exe http://127.0.0.1:8000/api/v1/forecast

# Прогноз на 10 дней
curl.exe http://127.0.0.1:8000/api/v1/forecast/10_days

# Состояние сервиса
curl.exe http://127.0.0.1:8000/api/v1/health
~~~

### Обновление через API

POST `/api/v1/refresh` защищён заголовком `X-Refresh-Token`. Чтобы включить его, задайте переменную окружения до запуска сервера:

~~~powershell
$env:WEATHER_API_REFRESH_TOKEN = "your-long-random-secret"
python -m uvicorn api:app --host 127.0.0.1 --port 8000
~~~

Вызов:

~~~powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/refresh -H "X-Refresh-Token: your-long-random-secret"
~~~

Если переменная не задана, API-обновление отключено. В таком случае обновляйте данные CLI-командой `python main.py`. Не публикуйте секретный токен в репозитории и не используйте демонстрационное значение в рабочем окружении.

### Структура ответа

Полный прогноз содержит `fetched_at_utc` и объект `forecasts`. Почасовые данные находятся в `hours`, дневные — в `days`. В каждой записи доступны timestamp, температура, описание неба, скорость ветра, порывы и направление ветра. Для дневной температуры могут использоваться `temperature_min_c` и `temperature_max_c`.

Дата и время прогноза соответствуют часовому поясу `Europe/Moscow`. Время формирования JSON хранится в UTC.

Коды ответа: `200` — успех, `401` — неверный токен, `404` — неизвестный или отсутствующий период, `409` — обновление уже выполняется, `502` — ошибка загрузки/разбора источника, `503` — прогноз ещё не создан или функция обновления отключена. Тело ошибки содержит поле `detail`.

## Резервные копии HTML

При успешной загрузке исходный HTML атомарно сохраняется в:

~~~text
data/html_backup/
├── today.html
├── tomorrow.html
├── 10_days.html
└── 2_weeks.html
~~~

При сетевой ошибке, HTTP-ошибке или пустом ответе сборщик использует последнюю сохранённую копию соответствующей страницы. Если копии ещё нет, обновление завершается понятной ошибкой. Папка исключена из Git.

## Обновление прогноза вручную

Можно обновить JSON без запуска веб-сервера:

~~~powershell
python main.py
~~~

Весь процесс загрузки и разбора вынесен в общий модуль `src/collector.py`; его используют и CLI, и API, поэтому логика парсинга остаётся единой.

## Тесты

~~~powershell
python -m unittest discover -s tests -v
~~~

Тесты покрывают парсер, HTML-кэш, HTTP-заголовки, API-маршруты и страницу документации.

## Экспорт интерфейса в PNG

Дополнительные инструменты:

~~~powershell
python -m pip install -r requirements-render.txt
python -m playwright install chromium
~~~

Экспорт:

~~~powershell
python scripts/render_weather.py
~~~

Для демонстрационных данных:

~~~powershell
python scripts/render_weather.py --demo
~~~

## Структура проекта

~~~text
weather-gorodets-v1/
├── api.py                     # FastAPI и HTTP endpoints
├── main.py                    # CLI-запуск парсера
├── requirements.txt
├── requirements-render.txt
├── src/
│   ├── collector.py           # общий сборщик для CLI и API
│   ├── models.py
│   ├── parser.py
│   └── storage.py
├── tests/
│   ├── test_api.py
│   ├── test_page_download.py
│   └── test_weather_parser.py
├── scripts/
│   └── render_weather.py
├── web/
│   ├── index.html             # интерфейс прогноза
│   ├── api-docs.html          # отдельная страница документации API
│   ├── styles.css
│   ├── app.js
│   └── demo_weather.json
└── data/
    ├── html_backup/           # локальные HTML-копии страниц Gismeteo
    └── weather.json           # сохранённые прогнозы
~~~
