# weather-gorodets-v1

Небольшой Python-парсер страницы погоды в Городце на Gismeteo.

## Задача 1. Загрузка страницы и вывод `<title>`

Скрипт `main.py` отправляет HTTP-запрос к странице
[Погода в Городце на Gismeteo](https://www.gismeteo.ru/weather-gorodets-4334/),
загружает HTML, извлекает текст тега `<title>` с помощью BeautifulSoup
и парсера `lxml`, а затем выводит его в консоль.

## Локальный запуск на Python 3.12 (Windows)

### 1. Проверить установку Python

В PowerShell выполните:

```powershell
py -3.12 --version
```

Команда должна показать версию Python 3.12.x.

### 2. Получить проект

Если репозиторий ещё не склонирован:

```powershell
git clone https://github.com/bubnovevgenyi-ux/weather-gorodets-v1.git
cd weather-gorodets-v1
```

Если проект уже находится на компьютере, перейдите в его каталог и получите
последние изменения:

```powershell
git pull origin main
```

### 3. Создать виртуальное окружение

```powershell
py -3.12 -m venv .venv
```

### 4. Активировать виртуальное окружение

```powershell
.venv\Scripts\Activate.ps1
```

Если PowerShell блокирует активацию скрипта, для текущего окна терминала
можно разрешить её командой:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

### 5. Установить зависимости

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 6. Запустить парсер

```powershell
python main.py
```

При успешной загрузке страницы в консоли появится заголовок:

```text
Title страницы: ...
```

## Структура проекта

```text
weather-gorodets-v1/
├── .venv/              # локальное виртуальное окружение (не коммитится)
├── main.py             # загрузка страницы и извлечение <title>
├── requirements.txt    # зависимости проекта
└── README.md            # инструкция
```

## Обработка ошибок

При ошибке HTTP-запроса или отсутствии тега `<title>` скрипт выводит сообщение
в stderr и завершается с кодом `1`.
