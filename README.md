# weather-gorodets-v1

Python-парсер прогноза погоды в Городце с Gismeteo. Запуск — локально на Python 3.12, без Docker.

## Что извлекается

Парсер находит блок страницы с атрибутом `data-widget="weather-parameters"` и извлекает из него:

- время прогноза формата `H:MM` (например, `0:00`, `9:00`, `12:00`);
- Unix timestamp;
- состояние неба (текст из `data-tooltip`);
- температуру воздуха, °C;
- скорость ветра, м/с;
- порывы ветра, м/с;
- направление ветра, если оно присутствует в HTML.

Изображения и ссылки на SVG-символы не сохраняются ни в модели, ни в JSON.

Строки виджета сопоставляются по позиции. Время формируется из Unix timestamp в часовом поясе Городца (`Europe/Moscow`), а не читается из текстового содержимого кастомного тега `<time-value>`. Это предотвращает пустые значения времени при изменении HTML-разметки.

В переданном HTML-фрагменте значения идут с шагом 3 часа; парсер сохраняет фактические временные точки, которые отдаёт сайт, и не создаёт отсутствующие почасовые значения.

## Структура хранения

В памяти прогноз представлен как `dict[int, HourlyWeather]`:

- ключ — Unix timestamp;
- значение — объект `HourlyWeather` с `dataclass(slots=True)`.

Такой индекс даёт быстрый поиск по времени (в среднем O(1)), а `slots=True` уменьшает накладные расходы на хранение объектов. В JSON данные также сохраняются с timestamp в качестве ключа.

Результат сохраняется в `data/weather.json`. В записи находятся только числовые и текстовые погодные показатели; изображений, путей к картинкам и SVG-кодов в данных нет.

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

При успешном запуске программа выведет таблицу в консоль и создаст JSON-файл.

Если PowerShell блокирует активацию виртуального окружения, разрешите запуск скриптов только для текущего окна терминала:

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
