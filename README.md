# weather-gorodets-v1

Python-парсер прогноза погоды в Городце с Gismeteo. Запуск — локально на Python 3.12, без Docker.

## Что извлекается

Программа загружает две страницы Gismeteo:

- Сегодня: https://www.gismeteo.ru/weather-gorodets-4334/
- Завтра: https://www.gismeteo.ru/weather-gorodets-4334/tomorrow/

Для каждой страницы парсер находит блок `data-widget="weather-parameters"` и извлекает:

- время прогноза формата `H:MM`;
- Unix timestamp;
- состояние неба (текст из `data-tooltip`);
- температуру воздуха, °C;
- скорость ветра, м/с;
- порывы ветра, м/с;
- направление ветра, если оно присутствует в HTML.

Время формируется из Unix timestamp в часовом поясе Городца (`Europe/Moscow`). Изображения и ссылки на SVG-символы не сохраняются.

Строки погодного виджета сопоставляются по позиции. Парсер проверяет, что количество временных точек одинаково во всех обязательных рядах. Он сохраняет реальные точки, которые отдаёт Gismeteo, и не генерирует отсутствующие часы.

## Структура данных

В памяти каждый прогноз представлен как `dict[int, HourlyWeather]`:

- ключ — Unix timestamp;
- значение — компактный объект `HourlyWeather` с `dataclass(slots=True)`.

Оба прогноза сохраняются в один файл `data/weather.json`, но в разных разделах:

- `forecasts.today` — «Погода сегодня»;
- `forecasts.tomorrow` — «Погода завтра».

У каждого раздела есть подпись, URL источника и словарь `hours`, индексированный по timestamp. В погодных записях хранятся только текстовые и числовые показатели, без картинок.

## Установка и запуск (Windows PowerShell)

Проверьте наличие Python 3.12:

```powershell
py -3.12 --version
```

Получите репозиторий или обновите существующую копию:

```powershell
git clone https://github.com/bubnovevgenyi-ux/weather-gorodets-v1.git
cd weather-gorodets-v1
```

Для существующего клона вместо повторного `git clone` выполните:

```powershell
git pull origin main
```

Создайте и активируйте виртуальное окружение:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

Установите зависимости:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Запустите парсер:

```powershell
python main.py
```

Программа последовательно загрузит обе страницы, выведет два отдельных блока в консоль и сохранит их в `data/weather.json`.

Если PowerShell блокирует активацию виртуального окружения:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## Структура проекта

```text
weather-gorodets-v1/
├── main.py
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── parser.py
│   └── storage.py
└── data/
    └── weather.json       # создаётся при запуске
```
