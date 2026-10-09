# Web-frontend: интерфейс сотрудника ГИБДД

Одностраничное веб-приложение на **React**. Через него сотрудник входит в систему, ведёт список розыска, получает оповещения о разыскиваемых автомобилях и смотрит историю. Работает с [backend](../backend/README.md) по REST и WebSocket.

Описание проекта в целом, бизнес-правила и ER-диаграмма: [корневой README](../README.md).

## Технологии

React 18, React Router 6, Redux Toolkit (состояние авторизации), Axios (запросы), Tailwind CSS (оформление), React-Toastify (уведомления), Heroicons (иконки). Сборка: Create React App.

## Требования

Node.js 18 или новее и запущенный backend.

## Быстрый старт

```powershell
cd web-frontend
copy .env.example .env      
npm install
npm start
```

Сайт откроется на http://localhost:3000. Backend по умолчанию ожидается на http://localhost:8000.

Войдите под тестовым сотрудником: логины и пароли лежат в `backend/seed_users.json` (шаблон: `backend/seed_users.example.json`).

## Настройки (`.env`)

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `REACT_APP_API_URL` | `http://localhost:8000/api` | Адрес API |
| `REACT_APP_WS_URL` | выводится из `REACT_APP_API_URL` | Адрес WebSocket, если он отличается |
| `REACT_APP_FOUND_PROMPT_DELAY_MS` | `60000` | Через сколько миллисекунд после «Принято» спрашивать «Автомобиль задержан?» |

Для демонстрации удобно поставить `REACT_APP_FOUND_PROMPT_DELAY_MS=10000`. Переменные читаются при запуске `npm start`: после изменения `.env` перезапустите.

## Страницы

| Адрес | Страница | Что делает |
|---|---|---|
| `/login` | Вход | Логин и пароль |
| `/dashboard` | Главная | Счётчики и оповещения без реакции |
| `/my-wanted` | Мой розыск | Список своих записей, добавление и удаление |
| `/all-wanted` | База розыска | Все записи, можно взять чужой розыск себе |
| `/map` | Карта | Карта камер, масштаб, подсветка сработавшей камеры |
| `/history` | История | Оповещения за сегодня, неделю или месяц |
| `/profile` | Профиль | Данные сотрудника |

Все страницы, кроме входа, доступны только после авторизации. Подробное описание каждой страницы и кнопок: [docs/pages.md](docs/pages.md).

## Структура

```
src/
  App.js                 маршруты
  config.js              адреса и настройки из .env
  services/api.js        настроенный Axios (токен, обработка 401)
  store/                 Redux: данные авторизации
  contexts/AlertContext  WebSocket и оповещения
  components/            Layout (меню), PrivateRoute, DetectionModal
  pages/                 страницы
public/                  карта города и 15 вариантов с подсвеченной камерой
docs/                    подробная документация
```

## Скрипты

| Команда | Что делает |
|---|---|
| `npm start` | Запуск для разработки |
| `npm run build` | Сборка для публикации в папку `build` |

## Документация

| Файл | О чём |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Устройство приложения: маршрутизация, состояние, запросы |
| [docs/pages.md](docs/pages.md) | Страницы, кнопки и вызовы API |
| [docs/alerts-flow.md](docs/alerts-flow.md) | Как приходит оповещение и что происходит дальше |
| [docs/configuration.md](docs/configuration.md) | Настройки и сборка |
| [docs/testing.md](docs/testing.md) | Чек-лист ручной проверки всех кнопок |
