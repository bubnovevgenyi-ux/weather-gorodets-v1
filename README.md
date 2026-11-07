# weather-gorodets-v1

Python-парсер прогноза погоды в Городце с Gismeteo. Запуск — локально на Python 3.12, без Docker.

## Что извлекается

Программа загружает две страницы Gismeteo:

- Сегодня: https://www.gismeteo.ru/weather-gorodets-4334/
- Завтра: https://www.gismeteo.ru/weather-gorodets-4334/tomorrow/

Для каждой страницы парсер находит погодный виджет и извлекает время прогноза, Unix timestamp, состояние неба, температуру, скорость ветра, порывы и направление ветра.

Время формируется из Unix timestamp в часовом поясе Городца (Europe/Moscow). Изображения не сохраняются в погодных данных.

## Структура данных

Оба прогноза сохраняются в data/weather.json в отдельных разделах:

- forecasts.today — «Погода сегодня»;
- forecasts.tomorrow — «Погода завтра».

Часовые записи индексируются по Unix timestamp.

## Установка и запуск парсера (Windows PowerShell)

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

Для уже склонированного проекта вместо git clone выполните git pull origin main.

## Графическая HTML/CSS-форма

После запуска python main.py откройте корень проекта в локальном веб-сервере:

~~~powershell
python -m http.server 8000
~~~

Перейдите в браузере по адресу:

http://127.0.0.1:8000/web/

Страница отображает две вкладки — «Сегодня» и «Завтра», временные карточки, температуру, состояние неба, ветер, порывы и график изменения температуры. Значки погоды рисуются inline SVG на основе текстового состояния неба; никаких картинок в JSON нет.

## Экспорт графической формы в PNG

Установите дополнительную зависимость для снимков страницы:

~~~powershell
python -m pip install -r requirements-render.txt
python -m playwright install chromium
~~~

Создайте два PNG-файла на основе актуального data/weather.json:

~~~powershell
python scripts/render_weather.py
~~~

Файлы появятся в каталоге output:

- output/weather_today.png
- output/weather_tomorrow.png

Для предварительного просмотра оформления на демонстрационных, неактуальных значениях:

~~~powershell
python scripts/render_weather.py --demo
~~~

Демонстрационный JSON лежит в web/demo_weather.json и помечен в интерфейсе как пример. Для реального отображения и экспорта не используйте --demo.

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
    ├── weather_today.png
    └── weather_tomorrow.png
~~~
