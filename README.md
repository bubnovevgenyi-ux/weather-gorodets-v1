# weather-gorodets-v1

Python-парсер прогноза погоды в Городце с Gismeteo. Запуск — локально на Python 3.12, без Docker.

## Что извлекается

Парсер находит блок страницы с атрибутом `data-widget="weather-parameters"` и извлекает из него:

- время прогноза и Unix timestamp;
- состояние неба (текст из `data-tooltip`);
- иконку состояния неба (SVG);
- температуру воздуха, °C;
- скорость ветра, м/с;
- порывы ветра, м/с;
- направление ветра, если оно присутствует в HTML.

Строки виджета сопоставляются по позиции. Для устойчивой идентификации используется Unix timestamp, а не только строка времени. В переданном HTML-фрагменте значения идут с шагом 3 часа; парсер сохраняет фактические временные точки, которые отдаёт сайт, и не создаёт отсутствующие почасовые значения.

## Структура хранения

В памяти прогноз представлен как `dict[int, HourlyWeather]`:

- ключ — Unix timestamp;
- значение — объект `HourlyWeather` с `dataclass(slots=True)`.

Такой индекс даёт быстрый поиск по времени (в среднем O(1)), а `slots=True` уменьшает накладные расходы на хранение объектов. В JSON данные также сохраняются с timestamp в качестве ключа.

Файлы результата создаются локально:

- `data/weather.json` — показатели по временным точкам;
- `assets/weather_icons/*.svg` — SVG-иконки. Одинаковые сочетания SVG-символов сохраняются один раз и переиспользуются в записях прогноза.

Иконка Gismeteo состоит из SVG-слоёв, ссылающихся на символы вида `#n_c3`, `#s1`. Парсер ищет определения этих символов в полном HTML документа и встраивает их в отдельные SVG-файлы. Если в HTML присутствует только фрагмент виджета без определений символов, картинка не будет создана: в JSON останутся коды символов, а программа выведет предупреждение.

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

При успешном запуске программа выведет таблицу в консоль и создаст JSON и SVG-файлы.

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
├── assets/weather_icons/   # генерируется при запуске
└── data/weather.json       # генерируется при запуске
```
