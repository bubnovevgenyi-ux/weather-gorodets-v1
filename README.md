# weather-gorodets-v1

Python 3.12-парсер прогноза погоды в Городце с Gismeteo. Запуск локально, без Docker.

## Источники прогнозов

Программа загружает четыре страницы:

| Раздел | Страница | Разрешение |
|---|---|---|
| \`today\` — «Погода сегодня» | https://www.gismeteo.ru/weather-gorodets-4334/ | Почасовой |
| \`tomorrow\` — «Погода завтра» | https://www.gismeteo.ru/weather-gorodets-4334/tomorrow/ | Почасовой |
| \`10_days\` — «Погода 10 дней» | https://www.gismeteo.ru/weather-gorodets-4334/10-days/ | По дням, 10 записей |
| \`2_weeks\` — «Погода 2 недели» | https://www.gismeteo.ru/weather-gorodets-4334/2-weeks/ | По дням, 14 записей |

Для дневных страниц извлекаются дата, состояние неба, температура (одно значение или минимум/максимум), скорость ветра, порывы и направление ветра. Дата строится по Unix timestamp в часовом поясе \`Europe/Moscow\`.

## Структура JSON

Все четыре прогноза записываются в \`data/weather.json\`. Почасовые записи хранятся в \`hours\`, дневные — в \`days\`. Тип данных дополнительно указан в поле \`resolution\`:

- \`forecasts.today.hours\`
- \`forecasts.tomorrow.hours\`
- \`forecasts.10_days.days\`
- \`forecasts.2_weeks.days\`

Данные каждого периода имеют собственные подпись и URL источника. Дневные и почасовые записи не смешиваются.

## Установка и запуск (Windows PowerShell)

~~~powershell
py -3.12 --version
git clone https://github.com/bubnovevgenyi-ux/weather-gorodets-v1.git
cd weather-gorodets-v1
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
~~~

Для уже склонированного проекта вместо \`git clone\` выполните \`git pull origin main\`.

## Тесты парсера

~~~powershell
python -m unittest discover -s tests -v
~~~

Тестовые HTML-фрагменты проверяют 10 и 14 дневных записей и разделение почасового/дневного JSON. Они не заменяют контрольную проверку на HTML, фактически возвращаемом Gismeteo.

## HTML/CSS-интерфейс

После запуска \`python main.py\` запустите локальный веб-сервер:

~~~powershell
python -m http.server 8000
~~~

Откройте http://127.0.0.1:8000/web/.

В интерфейсе есть четыре вкладки: «Сегодня», «Завтра», «10 дней» и «2 недели». Для первых двух отображаются почасовые карточки, для двух последних — календарные дневные карточки.

## Экспорт в PNG

Установите дополнительные инструменты:

~~~powershell
python -m pip install -r requirements-render.txt
python -m playwright install chromium
~~~

Сохраните PNG для всех четырёх периодов:

~~~powershell
python scripts/render_weather.py
~~~

Файлы появятся в \`output\`:

- \`weather_today.png\`
- \`weather_tomorrow.png\`
- \`weather_10_days.png\`
- \`weather_2_weeks.png\`

Только для просмотра макета на демонстрационных данных:

~~~powershell
python scripts/render_weather.py --demo
~~~

\`web/demo_weather.json\` содержит вымышленные значения и помечается в интерфейсе как демо. Для фактических прогнозов используйте JSON, созданный \`python main.py\`.

## Структура проекта

~~~text
weather-gorodets-v1/
├── main.py
├── requirements.txt
├── requirements-render.txt
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── parser.py
│   └── storage.py
├── tests/
│   └── test_weather_parser.py
├── scripts/
│   └── render_weather.py
├── web/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── demo_weather.json
├── data/
│   └── weather.json
└── output/
~~~
