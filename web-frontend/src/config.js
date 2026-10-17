export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Адрес WebSocket. Если API_URL относительный (например, /api в Docker, где nginx проксирует
// запросы к backend), берём адрес самой страницы: сайт и API находятся на одном домене.
function buildWsUrl() {
  if (process.env.REACT_APP_WS_URL) {
    return process.env.REACT_APP_WS_URL;
  }
  if (API_URL.startsWith('/')) {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${protocol}://${window.location.host}${API_URL.replace(/\/api\/?$/, '')}/ws`;
  }
  return API_URL.replace(/^http/, 'ws').replace(/\/api\/?$/, '') + '/ws';
}

export const WS_URL = buildWsUrl();

export const FOUND_PROMPT_DELAY_MS =
  Number(process.env.REACT_APP_FOUND_PROMPT_DELAY_MS) || 60000;
