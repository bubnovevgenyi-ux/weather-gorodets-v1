# weather-gorodets-v1

Небольшой Python-парсер страницы погоды в Городце на Gismeteo.

## Задача 1. Загрузка страницы и вывод `<title>`

Скрипт `main.py` отправляет HTTP-запрос к странице
[Погода в Городце на Gismeteo](https://www.gismeteo.ru/weather-gorodets-4334/),
загружает HTML, извлекает текст тега `<title>` с помощью BeautifulSoup
и парсера `lxml`, а затем выводит его в консоль.

## Запуск в Docker

Требуется установленный и запущенный Docker (например, Docker Desktop на Windows).

### 1. Получить проект

Если репозиторий ещё не склонирован:

```bash
git clone https://github.com/bubnovevgenyi-ux/weather-gorodets-v1.git
cd weather-gorodets-v1
```

Если проект уже есть на компьютере, перейдите в его каталог и обновите код:

```bash
git pull origin main
```

### 2. Собрать Docker-образ

В каталоге проекта выполните:

```bash
docker build -t weather-gorodets .
```

### 3. Запустить контейнер

```bash
docker run --rm weather-gorodets
```

Контейнер загрузит страницу Gismeteo, выведет заголовок в терминал и завершит работу. Параметр `--rm` автоматически удалит остановленный контейнер.

Ожидаемый формат вывода:

```text
Title страницы: ...
```

### Повторный запуск после обновления кода

После получения изменений из GitHub пересоберите образ и запустите контейнер:

```bash
git pull origin main
docker build --pull -t weather-gorodets .
docker run --rm weather-gorodets
```

## Локальный запуск без Docker (для разработки)

Требуется Python 3.9 или новее.

```bash
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Установка зависимостей и запуск:

```bash
python -m pip install -r requirements.txt
python main.py
```

## Обработка ошибок

При ошибке HTTP-запроса или отсутствии тега `<title>` скрипт выводит сообщение
в stderr и завершается с кодом `1`.

## Структура проекта

```text
weather-gorodets-v1/
├── .dockerignore
├── Dockerfile
├── main.py
├── requirements.txt
└── README.md
```
