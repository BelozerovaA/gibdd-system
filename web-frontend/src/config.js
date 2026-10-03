// Адреса и настройки берутся из web-frontend/.env (см. .env.example),
// если переменные не заданы, используются значения по умолчанию для локального запуска.

export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// WebSocket живёт на том же сервере, что и API: http://host:8000/api -> ws://host:8000/ws
export const WS_URL =
  process.env.REACT_APP_WS_URL ||
  API_URL.replace(/^http/, 'ws').replace(/\/api\/?$/, '') + '/ws';

// Через сколько миллисекунд после «Принято» спрашивать «Автомобиль задержан?»
export const FOUND_PROMPT_DELAY_MS =
  Number(process.env.REACT_APP_FOUND_PROMPT_DELAY_MS) || 60000;
