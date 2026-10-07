# Backend: API системы розыска ГИБДД

Серверная часть: REST API и WebSocket на **FastAPI**, данные в **MySQL**. Обслуживает веб-клиент ([`web-frontend`](../web-frontend/README.md)) и содержит симулятор камер, который создаёт оповещения о разыскиваемых автомобилях.

Описание проекта в целом, бизнес-правила и ER-диаграмма: [корневой README](../README.md).

## Технологии

Python 3.12, FastAPI, SQLAlchemy 2, PyMySQL, python-jose (JWT), WebSocket, python-docx и openpyxl (отчёты).

## Требования

- **Python 3.12.** На более новых версиях (3.13, 3.14) установка зависимостей падает: для закреплённой в `requirements.txt` версии `pydantic-core` нет готовой сборки, и pip пытается собирать её из исходников через Rust.
- MySQL 8 (или совместимый).

## Быстрый старт

```powershell
cd backend

# 1. БД
#    CREATE DATABASE gibdd_db CHARACTER SET utf8mb4;

# 2. окружение и зависимости
py -3.12 -m venv venv
venv\Scripts\activate                 
pip install -r requirements.txt

# 3. Настройки
copy .env.example .env                
copy seed_users.example.json seed_users.json   

# 4. тестовые данные и запуск
python seed.py
python -m uvicorn app.main:app --reload --port 8000
```

Проверка: http://localhost:8000/ вернёт `{"message": "GIBDD API", "status": "running"}`. Интерактивная документация: http://localhost:8000/docs.

Для запуска мобильного клиента на телефоне добавьте `--host 0.0.0.0` к команде `uvicorn`.

## Тестовые сотрудники

Логины и пароли **не хранятся в коде**: `seed.py` читает их из `seed_users.json`. В репозитории лежит шаблон [`seed_users.example.json`](seed_users.example.json), из которого вы создаёте свой файл (шаг 3 выше). Сам `seed_users.json` в git не попадает. Подробности: [docs/configuration.md](docs/configuration.md#тестовые-данные-seedpy-и-seed_usersjson).

## Настройки (`.env`)

Главные переменные: `DATABASE_URL`, `SECRET_KEY`, `DETECTION_INTERVAL_SECONDS`, `SEED_USERS_FILE`, `SMTP_USER`, `SMTP_PASSWORD`. Полная таблица: [docs/configuration.md](docs/configuration.md).

## Структура

```
seed.py                  тестовые данные
seed_data.py             загрузка тестовых сотрудников из JSON
seed_users.example.json  шаблон тестовых сотрудников
tests/                   автотесты
app/
  main.py                запуск приложения, маршруты, WebSocket
  models.py, schemas.py  таблицы и форматы данных
  auth.py                токены
  routes/                HTTP-маршруты
  services/              симулятор камер, письма, отчёты
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
| Симулятор | `POST /api/simulator/start`, `/stop`, `/resume` |
| Реальное время | WebSocket `/ws/{employee_id}?token=...` |

## Тесты

```powershell
python -m unittest discover -s tests -v
```

Тесты не требуют базы данных и дополнительных библиотек. Они проверяют загрузку тестовых сотрудников из JSON (в том числе ошибки в файле и отсутствие паролей в `seed.py`) и выбор почтового сервера.

## Документация

| Файл | О чём |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Устройство backend, слои, как оповещение доходит до клиента |
| [docs/api.md](docs/api.md) | Все маршруты и WebSocket, с примерами |
| [docs/database.md](docs/database.md) | Таблицы, поля, связи, ER-диаграмма |
| [docs/simulator.md](docs/simulator.md) | Как работает симулятор камер |
| [docs/configuration.md](docs/configuration.md) | Переменные окружения, почта, тестовые данные |
| [docs/security.md](docs/security.md) | Что сделано для безопасности и что нужно доработать |

## Известные ограничения

Пароли в БД хранятся открытым текстом, CORS открыт для всех адресов, нет HTTPS. Это допустимо для учебного проекта, но не для боевого: полный список и способы исправления в [docs/security.md](docs/security.md).
