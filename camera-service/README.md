# Сервис камер

Отдельный сервис, который изображает работу камер видеофиксации. Он **не входит в backend**: это свой процесс и свой контейнер, у него нет доступа к базе данных. С сервисом ГИБДД он общается только сообщениями по [протоколу](docs/protocol.md).

Реальной системы распознавания номеров в проекте нет, поэтому «увидеть автомобиль» сервис умеет двумя способами: сам, по таймеру, или по команде вручную (удобно для демонстрации). Для сервиса ГИБДД это неотличимо от настоящей камеры: он получает событие и не знает, откуда оно взялось. Заменить этот сервис настоящей системой можно, не трогая остальной код, лишь бы она говорила на том же протоколе.

Общая картина проекта: [корневой README](../README.md) и [docs/architecture.md](../docs/architecture.md).

## Что делает сервис

1. **Получает от сервиса ГИБДД список разыскиваемых ГРЗ** (`PUT /v1/watchlist`).
2. **Раз в `CAMERA_INTERVAL_SECONDS` секунд** выбирает случайный ГРЗ из списка и случайную работающую камеру и **отправляет событие** в сервис ГИБДД (`POST /api/camera-events`).
3. **По команде** фиксирует указанный автомобиль немедленно (`POST /v1/detections`).

Если сервис ГИБДД недоступен, событие отправляется повторно (до 3 попыток, с одним и тем же `event_id`, поэтому оповещение не задвоится).

## Запуск

**В Docker** вместе со всей системой: [docs/docker.md](../docs/docker.md).

**Отдельно, без Docker** (нужен только Python 3.12, зависимостей нет; в Docker используется та же версия):

```powershell
cd camera-service
$env:SERVICE_TOKEN = "тот-же-токен-что-в-backend"
$env:GIBDD_URL = "http://localhost:8000"
$env:CAMERA_INTERVAL_SECONDS = "10"      # для демонстрации
python -m app.main
```

Linux и macOS: `SERVICE_TOKEN=... GIBDD_URL=http://localhost:8000 python -m app.main`.

Проверка: http://localhost:9000/health покажет `{"status": "ok", "cameras": 15, "watchlist": 0}`. Список розыска появится, как только запущен сервис ГИБДД с тем же `SERVICE_TOKEN` и адресом `CAMERA_SERVICE_URL=http://localhost:9000`.

## Ручная фиксация

Чтобы не ждать таймера, «покажите» камере автомобиль командой:

```powershell
$token = "ВАШ_SERVICE_TOKEN"
$body  = [System.Text.Encoding]::UTF8.GetBytes('{"plate":"А123ВК43","camera_code":"CAM-08"}')
Invoke-RestMethod -Method Post -Uri http://localhost:9000/v1/detections `
  -Headers @{ "X-Service-Token" = $token } -ContentType "application/json; charset=utf-8" -Body $body
```

В ответе будет видно, что решил сервис ГИБДД: `accepted` (оповещение создано) или `ignored` с причиной. Подробно: [docs/protocol.md](docs/protocol.md#ручная-фиксация).

## Настройки

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `SERVICE_TOKEN` | нет | Общий секрет с сервисом ГИБДД. **Обязателен** |
| `GIBDD_URL` | `http://localhost:8000` | Адрес сервиса ГИБДД |
| `CAMERA_INTERVAL_SECONDS` | `60` | Как часто камеры «видят» автомобиль из списка |
| `PORT` | `9000` | Порт сервиса камер |
| `ENABLE_MANUAL_DETECTIONS` | `true` | Разрешить ручную фиксацию |

Остальные (таймаут, число попыток, файл камер): [docs/configuration.md](docs/configuration.md).

## Структура

```
app/
  main.py            запуск: настройки, потоки, остановка по сигналу
  config.py          настройки из переменных окружения
  cameras.py         загрузка списка камер
  cameras.json       15 камер: код, адрес, координаты
  watchlist.py       список ГРЗ, присланный сервисом ГИБДД
  gibdd_client.py    отправка событий с повторами
  emitter.py         имитация работы камер
  server.py          HTTP-интерфейс протокола
tests/               автотесты
docs/                подробная документация
Dockerfile
```

## Тесты

```powershell
python -m unittest discover -s tests -v
```

Всего 58 тестов, зависимостей не нужно. Они запускают настоящие HTTP-серверы на свободных портах, проверяют протокол, повторы, ошибки и согласованность с backend, а один тест запускает оба сервиса вместе. Подробно: [docs/testing.md](docs/testing.md).

## Документация

| Файл | О чём |
|---|---|
| [docs/protocol.md](docs/protocol.md) | Протокол обмена с сервисом ГИБДД: запросы, ответы, ошибки, повторы |
| [docs/architecture.md](docs/architecture.md) | Устройство сервиса, потоки, почему без фреймворков |
| [docs/configuration.md](docs/configuration.md) | Все переменные окружения, формат файла камер |
| [docs/testing.md](docs/testing.md) | Автотесты и ручная проверка |
