# weather-gorodets-v1

Веб-сервис прогноза погоды в Городце. Стек: Python 3.12, FastAPI, Jinja2, Requests, BeautifulSoup, lxml и HTML/CSS. Данные загружаются парсером Gismeteo, подготавливаются на сервере и отображаются HTML-шаблонами FastAPI.

## Возможности

- Почасовой прогноз на сегодня и завтра.
- Дневной прогноз на 10 дней и 2 недели.
- Серверный HTML-рендеринг карточек, сводных показателей и SVG-графика температуры.
- Переключение периодов обычными GET-запросами — JavaScript для формирования прогноза не используется.
- HTTP API с JSON-ответами и проверкой состояния сервиса.
- Стандартная документация FastAPI: Swagger UI, ReDoc и схема OpenAPI.
- Сохранение HTML-страниц Gismeteo в `data/html_backup/` и использование последней копии при сетевой ошибке.

## Источники данных

| Раздел | URL | Данные |
|---|---|---|
| `today` — сегодня | https://www.gismeteo.ru/weather-gorodets-4334/ | Почасовой прогноз |
| `tomorrow` — завтра | https://www.gismeteo.ru/weather-gorodets-4334/tomorrow/ | Почасовой прогноз |
| `10_days` — 10 дней | https://www.gismeteo.ru/weather-gorodets-4334/10-days/ | 10 дневных записей |
| `2_weeks` — 2 недели | https://www.gismeteo.ru/weather-gorodets-4334/2-weeks/ | 14 дневных записей |

## Установка и запуск (Windows PowerShell)

```powershell
py -3.12 --version
git clone https://github.com/bubnovevgenyi-ux/weather-gorodets-v1.git
cd weather-gorodets-v1

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Запуск приложения, API и веб-интерфейса
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

При первом запуске FastAPI автоматически загружает четыре страницы Gismeteo и создаёт `data/weather.json`, если сохранённого прогноза ещё нет. Загрузка выполняется в рабочем потоке и не блокирует event loop. Если Gismeteo временно недоступен, сервер всё равно запускается: интерфейс покажет состояние без данных, а API вернёт диагностическую информацию. Последующие запуски используют сохранённый прогноз.

После запуска откройте:

- Веб-интерфейс: http://127.0.0.1:8000/
- Swagger UI (FastAPI): http://127.0.0.1:8000/docs
- ReDoc (FastAPI): http://127.0.0.1:8000/redoc
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

Для уже склонированного проекта получите изменения командой `git pull origin main` после слияния обновлений в основную ветку.

## Отладка локального FastAPI из PyCharm

Этот сценарий предназначен для разработки на одном личном компьютере: PyCharm, Python и Uvicorn работают локально. **Python Debug Server** нужен, когда приложение запускается отдельным процессом из терминала, а не кнопкой Debug в конфигурации самого приложения. SSH, сетевой туннель, удалённый сервер и Path mappings не нужны.

### 1. Установите pydevd-pycharm в окружение проекта

В PyCharm откройте **Run | Edit Configurations... | + | Python Debug Server**. В блоке **Update your script** найдите команду установки с версией pydevd-pycharm, соответствующей вашей сборке PyCharm. Выполните именно эту команду в терминале проекта, используя то же виртуальное окружение, из которого будет запускаться Uvicorn.

Чтобы использовать подготовленный файл зависимостей, замените строку pydevd-pycharm в requirements-debug.txt на точную версию из команды PyCharm, например pydevd-pycharm~=ВАШ_BUILD_NUMBER, затем выполните:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-debug.txt
```

Не устанавливайте произвольную версию пакета: она должна соответствовать сборке PyCharm.

### 2. Настройте Python Debug Server

1. В PyCharm откройте **Run | Edit Configurations...**.
2. Нажмите **+** и выберите **Python Debug Server**.
3. В поле **IDE host name** оставьте localhost.
4. Укажите порт 5678.
5. Поле **Path mappings** оставьте пустым — код выполняется на этом же компьютере.
6. Нажмите **Debug**. В окне Debug появится сообщение об ожидании подключения.

### 3. Включите отладчик в приложении

В локальном файле .env в корне проекта укажите:

```dotenv
PYCHARM_DEBUG=1
PYCHARM_DEBUG_HOST=localhost
PYCHARM_DEBUG_PORT=5678
PYCHARM_DEBUG_SUSPEND=0
```

PYCHARM_DEBUG_SUSPEND=0 означает, что приложение продолжит запуск и будет останавливаться только на установленных breakpoint. Значение 1 приостановит исполнение сразу после подключения к PyCharm.

### 4. Запустите FastAPI локально

Убедитесь, что активировано то же виртуальное окружение, в которое установлен pydevd-pycharm. Запустите Uvicorn в обычном терминале PyCharm или PowerShell:

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --workers 1
```

После подключения ставьте breakpoint в файлах проекта. Когда выполнение дойдёт до такого места, PyCharm остановит процесс и позволит просматривать переменные и выполнять пошаговую отладку.

Чтобы отключить отладчик, установите PYCHARM_DEBUG=0 в .env и перезапустите Uvicorn. В обычном режиме пакет отладчика не импортируется.

Официальная инструкция JetBrains: https://www.jetbrains.com/help/pycharm/remote-debugging-with-product.html

## HTTP API

Базовый префикс: `/api/v1`.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/` | Серверно отрендеренная страница прогноза |
| `GET` | `/?period=today` | Почасовой прогноз на сегодня |
| `GET` | `/?period=tomorrow` | Почасовой прогноз на завтра |
| `GET` | `/?period=10_days` | Дневной прогноз на 10 дней |
| `GET` | `/?period=2_weeks` | Дневной прогноз на 2 недели |
| `GET` | `/api/v1/health` | Статус сервиса, наличие данных и HTML-копий |
| `GET` | `/api/v1/forecast` | Все четыре периода прогноза в JSON |
| `GET` | `/api/v1/forecast/{period}` | Один период в JSON |
| `GET` | `/api/v1/forecast/{period}/image` | Изображение прогноза JPEG (для Telegram и мобильных устройств) |
| `POST` | `/api/v1/refresh` | Повторная загрузка и разбор страниц Gismeteo |

Примеры:

```powershell
# Полный прогноз в JSON
curl.exe http://127.0.0.1:8000/api/v1/forecast

# Прогноз на 10 дней в JSON
curl.exe http://127.0.0.1:8000/api/v1/forecast/10_days

# Изображение прогноза на 10 дней (JPEG)
curl.exe http://127.0.0.1:8000/api/v1/forecast/10_days/image --output weather_10_days.jpg

# Состояние сервиса
curl.exe http://127.0.0.1:8000/api/v1/health
```

### Обновление прогноза

POST `/api/v1/refresh` защищён заголовком `X-Refresh-Token`. Токен хранится локально в файле `.env` в корне проекта. Приложение загружает этот файл автоматически с помощью `python-dotenv`; системная переменная окружения имеет приоритет над значением из файла.

Создайте токен в Windows PowerShell:

```powershell
Copy-Item .env.example .env
$token = python -c "import secrets; print(secrets.token_urlsafe(32))"
"WEATHER_API_REFRESH_TOKEN=$token" | Set-Content -Encoding ascii .env

# Запустить или перезапустить FastAPI после сохранения .env
python -m uvicorn api:app --host 127.0.0.1 --port 8000

# Обновить прогноз через API
curl.exe -X POST http://127.0.0.1:8000/api/v1/refresh -H "X-Refresh-Token: $token"
```

Если сервер уже был запущен до создания или изменения `.env`, перезапустите его. Файл `.env` исключён из Git через `.gitignore`, поэтому секрет не попадёт в коммиты. Не передавайте токен в браузерный JavaScript и не публикуйте его.

Проверить, увидел ли сервис токен, можно через `GET /api/v1/health`: поле `refresh_enabled` должно быть `true`. Само значение токена API не раскрывает. Если токен не настроен, POST вернёт `503`; если заголовок отсутствует или не совпадает — `401`. При одновременном обновлении будет возвращён `409`.

## Серверный рендеринг

Маршрут `GET /` читает сохранённый JSON, передаёт выбранный период в `src/presentation.py` и отображает `templates/index.html` через Jinja2. Подготовка подписей, температурных диапазонов, статистики ветра и SVG-графика выполняется на сервере. CSS хранится отдельно от Jinja2-шаблонов в `static/css/` и раздаётся FastAPI по префиксу `/static`. Документация API предоставляется FastAPI по стандартным адресам `/docs`, `/redoc` и `/openapi.json`.

Переключатели периодов — обычные ссылки вида `/?period=10_days`. Браузер получает полностью сформированную HTML-страницу; клиентский JavaScript больше не дублирует логику визуализации.

## Резервные копии HTML

При успешной загрузке исходный HTML атомарно сохраняется в:

```text
data/html_backup/
├── today.html
├── tomorrow.html
├── 10_days.html
└── 2_weeks.html
```

При сетевой ошибке, HTTP-ошибке или пустом ответе сборщик использует последнюю сохранённую копию соответствующей страницы. Если копии ещё нет, обновление завершается ошибкой; интерфейс и API при этом остаются доступными. События загрузки и ошибки выводятся через стандартный механизм логирования Python, а не через отдельный консольный сценарий.

## Тесты

```powershell
python -m unittest discover -s tests -v
```

Тесты покрывают парсер, HTML-кэш, HTTP-заголовки, JSON API, серверный HTML-рендеринг, стандартную документацию FastAPI, HTTP-эндпоинт генерации JPEG и конфигурацию удалённого отладчика PyCharm.

## Изображения прогноза

FastAPI генерирует JPEG-карточку непосредственно в HTTP-ответе. Изображение создаётся в памяти с помощью Pillow: временные файлы и отдельный CLI-скрипт не требуются. Ширина карточки — 1080 px, высота зависит от количества записей прогноза.

Доступны адреса:

- `GET /api/v1/forecast/today/image`
- `GET /api/v1/forecast/tomorrow/image`
- `GET /api/v1/forecast/10_days/image`
- `GET /api/v1/forecast/2_weeks/image`

Пример загрузки изображения на диск:

```powershell
curl.exe http://127.0.0.1:8000/api/v1/forecast/10_days/image --output weather_10_days.jpg
```

URL можно открыть в браузере телефона или передать Telegram Bot API как фотографию. Ответ имеет MIME-тип `image/jpeg` и заголовок `Content-Disposition: inline`.

## Структура проекта

```text
weather-gorodets-v1/
├── api.py                     # FastAPI, JSON API и серверные маршруты
├── requirements.txt
├── templates/
│   └── index.html             # Jinja2-шаблон прогноза
├── src/
│   ├── collector.py           # сборщик данных Gismeteo
│   ├── presentation.py        # модель представления и SVG-график
│   ├── models.py
│   ├── parser.py
│   └── storage.py
├── tests/
│   ├── test_api.py
│   ├── test_page_download.py
│   ├── test_weather_parser.py
│   └── test_api_image.py
├── static/
│   └── css/
│       └── styles.css
└── data/
    ├── html_backup/           # локальные HTML-копии страниц Gismeteo
    └── weather.json           # сохранённые прогнозы
```
