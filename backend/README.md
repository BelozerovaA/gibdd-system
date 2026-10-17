# Backend: сервис ГИБДД

Серверная часть: REST API и WebSocket на **FastAPI**, данные в **MySQL**. Обслуживает клиентов ([сайт](../web-frontend/README.md) и [мобильное приложение](../AvtoDozor/README.md)), хранит розыск, принимает события от [сервиса камер](../camera-service/README.md), создаёт оповещения и доставляет их сотрудникам.

Камеры в backend не входят: это отдельный сервис, с которым backend общается по [протоколу](../camera-service/docs/protocol.md). Описание проекта в целом: [корневой README](../README.md), архитектура: [docs/architecture.md](../docs/architecture.md). ER-диаграмма: [docs/er-diagram.png](../docs/er-diagram.png).

## Технологии

Python 3.12, FastAPI, SQLAlchemy 2, PyMySQL, python-jose (JWT), WebSocket, python-docx и openpyxl (отчёты).

## Требования

- **Python 3.12.** На более новых версиях (3.13, 3.14) установка зависимостей падает: для закреплённой в `requirements.txt` версии `pydantic-core` нет готовой сборки, и pip пытается собирать её из исходников через Rust.
- MySQL 8 (или совместимый).

В Docker ничего из этого ставить не нужно: [docs/docker.md](../docs/docker.md).

## Запуск в Docker

Backend запускается вместе со всей системой командой `docker compose up --build` из корня репозитория: [docs/docker.md](../docs/docker.md). Образ собирается по [`Dockerfile`](Dockerfile), а при старте скрипт [`docker-entrypoint.sh`](docker-entrypoint.sh) дожидается базы данных, заполняет её тестовыми данными и запускает сервер.

## Быстрый старт без Docker

```powershell
cd backend

# 1. База данных (в MySQL)
#    CREATE DATABASE gibdd_db CHARACTER SET utf8mb4;

# 2. Окружение и зависимости
py -3.12 -m venv venv
venv\Scripts\activate                 # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt

# 3. Настройки
copy .env.example .env                # впишите пароль MySQL, SECRET_KEY и SERVICE_TOKEN
copy seed_users.example.json seed_users.json   # тестовые сотрудники (логины и пароли)

# 4. Тестовые данные и запуск
python seed.py
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка: http://localhost:8000/ вернёт `{"message": "GIBDD API", "status": "running"}`. Интерактивная документация: http://localhost:8000/docs.

`--host 0.0.0.0` нужен, чтобы к серверу мог подключиться телефон. Оповещений без сервиса камер не будет: запустите его ([инструкция](../camera-service/README.md#запуск)) с тем же `SERVICE_TOKEN` и укажите его адрес в `CAMERA_SERVICE_URL` (по умолчанию в `.env.example` это `http://localhost:9000`).

## Тестовые сотрудники

Логины и пароли **не хранятся в коде**: `seed.py` читает их из `seed_users.json`. В репозитории лежит шаблон [`seed_users.example.json`](seed_users.example.json), из которого вы создаёте свой файл (шаг 3 выше). Сам `seed_users.json` в git не попадает. Подробности: [docs/configuration.md](docs/configuration.md#тестовые-данные-seedpy-и-seed_usersjson).

## Настройки (`.env`)

Главные переменные: `DATABASE_URL`, `SECRET_KEY`, `SERVICE_TOKEN`, `CAMERA_SERVICE_URL`, `ALERT_COOLDOWN_SECONDS`, `SEED_USERS_FILE`, `SMTP_USER`, `SMTP_PASSWORD`. Полная таблица: [docs/configuration.md](docs/configuration.md).

## Структура

```
Dockerfile, docker-entrypoint.sh   образ и запуск в контейнере
seed.py                  тестовые данные
seed_data.py             загрузка тестовых сотрудников из JSON
seed_users.example.json  шаблон тестовых сотрудников
tests/                   автотесты
app/
  main.py                запуск приложения, маршруты, WebSocket
  models.py, schemas.py  таблицы и форматы данных
  auth.py                токены входа
  service_auth.py        проверка токена сервиса камер
  routes/                HTTP-маршруты
  services/              правила оповещений, события камер, связь с сервисом камер, письма, отчёты
  websocket/             соединения WebSocket
docs/                    подробная документация
```

## Основные маршруты

Полный список с примерами: [docs/api.md](docs/api.md).

| Группа | Маршруты |
|---|---|
| Вход | `POST /api/auth/login` |
| Профиль | `GET /api/employees/me` |
| Розыск | `GET /api/wanted/my`, `GET /api/wanted/all`, `POST /api/wanted/add`, `POST /api/wanted/take/{id}`, `DELETE /api/wanted/{plate}` |
| Оповещения | `GET /api/alerts/history`, `PUT /api/alerts/{id}/reaction`, `PUT /api/alerts/{id}/found`, экспорт в Word и Excel |
| События камер | `POST /api/camera-events` (вызывает сервис камер, нужен `X-Service-Token`) |
| Реальное время | WebSocket `/ws/{employee_id}?token=...` |

## Тесты

```powershell
python -m unittest discover -s tests -v
```

Тесты не требуют базы данных и дополнительных библиотек (65 тестов). Они проверяют правила оповещений (когда оповещение создаётся, а когда нет), отправку списка розыска камерам настоящим HTTP-сервером, менеджер WebSocket, загрузку тестовых сотрудников из JSON (в том числе ошибки в файле и отсутствие паролей в `seed.py`) и выбор почтового сервера.

## Документация

| Файл | О чём |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Устройство backend, слои, как оповещение доходит до клиента |
| [docs/api.md](docs/api.md) | Все маршруты и WebSocket, с примерами |
| [docs/camera-events.md](docs/camera-events.md) | События от сервиса камер: правила обработки, отправка списка розыска |
| [docs/database.md](docs/database.md) | Таблицы, поля, связи, ER-диаграмма |
| [docs/configuration.md](docs/configuration.md) | Переменные окружения, почта, тестовые данные |
| [docs/security.md](docs/security.md) | Что сделано для безопасности и что нужно доработать |

## Известные ограничения

Пароли в БД хранятся открытым текстом, CORS открыт для всех адресов, нет HTTPS. Это допустимо для учебного проекта, но не для боевого: полный список и способы исправления в [docs/security.md](docs/security.md).
