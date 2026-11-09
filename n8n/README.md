# n8n: Telegram-бот погоды в Городце

Файл workflow: `workflows/telegram_weather_gorodets.json`.

## Что делает сценарий

1. Telegram Trigger принимает сообщения и нажатия inline-кнопок.
2. Команды `/start` и `/menu` отправляют приветствие с четырьмя inline-кнопками: «Сегодня», «Завтра», «10 дней», «14 дней».
3. Нажатие кнопки обрабатывается как callback query; бот подтверждает нажатие.
4. HTTP Request загружает JPEG из существующего FastAPI endpoint:
   `GET /api/v1/forecast/{period}/image`.
5. Telegram отправляет картинку в чат, повторно прикладывая inline-клавиатуру для выбора другого периода.

Для кнопок используются ключи API:
- Сегодня: `today`
- Завтра: `tomorrow`
- 10 дней: `10_days`
- 14 дней: `2_weeks`

## Подготовка и импорт

1. Запустите FastAPI из корня проекта:
   `python -m uvicorn api:app --host 0.0.0.0 --port 8000`.
2. В n8n выберите **Import from File** и импортируйте `workflows/telegram_weather_gorodets.json`.
3. Создайте Telegram API credential в n8n (токен бота от BotFather) и выберите его в узлах **Telegram Trigger**, **Send welcome menu**, **Answer callback query** и **Send forecast photo**.
4. Откройте узел **Get forecast image** и проверьте URL API. В workflow указан адрес `http://host.docker.internal:8000` — он подходит, когда n8n запущен в Docker Desktop, а FastAPI работает на хост-компьютере.
5. Если n8n и FastAPI работают в одной Docker-сети, замените host на DNS-имя сервиса API, например `http://weather-api:8000`. Если n8n запущен непосредственно на том же компьютере, обычно используйте `http://127.0.0.1:8000`. Для n8n Cloud укажите публичный HTTPS-адрес FastAPI.
6. Активируйте workflow и отправьте боту команду `/start`.

## Требования к размещению

- Telegram Trigger использует webhook, поэтому ваш экземпляр n8n должен быть доступен Telegram по публичному HTTPS URL. При работе за reverse proxy задайте корректный внешний webhook URL в конфигурации n8n.
- FastAPI должен быть доступен из процесса n8n по адресу, указанному в узле **Get forecast image**.
- Эндпоинты получения прогноза и изображения публичные и не требуют `WEATHER_API_REFRESH_TOKEN`. Токен нужен только для `POST /api/v1/refresh`.

## Проверка

Проверьте API напрямую:

```bash
curl http://127.0.0.1:8000/api/v1/health
curl --output forecast.jpg http://127.0.0.1:8000/api/v1/forecast/today/image
```

В Telegram отправьте `/start`, затем нажмите каждую кнопку. В ответ бот должен отправить JPEG-карточку соответствующего периода.

## Важное замечание

У Telegram есть ограничение: для одного бота одновременно должен быть зарегистрирован только один Telegram Trigger webhook. Не включайте параллельно второй workflow с Telegram Trigger для того же bot token.

Полезные документы:
- [Telegram Trigger в n8n](https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.telegramtrigger/)
- [Telegram node в n8n](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.telegram/)
