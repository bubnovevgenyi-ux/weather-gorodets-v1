# weather-gorodets-v1

Небольшой Python-парсер страницы погоды в Городце на Gismeteo.

## Задача 1. Загрузка страницы и вывод `<title>`

Скрипт `main.py` отправляет HTTP-запрос к странице
[Погода в Городце на Gismeteo](https://www.gismeteo.ru/weather-gorodets-4334/),
загружает HTML, извлекает текст тега `<title>` с помощью BeautifulSoup
и парсера `lxml`, а затем выводит его в консоль.

### Установка

Требуется Python 3.9 или новее.

Создайте и активируйте виртуальное окружение:

```bash
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\\Scripts\\Activate.ps1
```

Установите зависимости:

```bash
python -m pip install -r requirements.txt
```

### Запуск

```bash
python main.py
```

При успешной загрузке в консоли появится строка с заголовком страницы:

```text
Title страницы: ...
```

При ошибке HTTP-запроса или отсутствии тега `<title>` скрипт выведет
сообщение в stderr и завершится с кодом `1`.

## Структура проекта

```text
weather-gorodets-v1/
├── main.py
├── requirements.txt
└── README.md
```
