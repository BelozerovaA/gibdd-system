export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
export const WS_URL =
  process.env.REACT_APP_WS_URL ||
  API_URL.replace(/^http/, 'ws').replace(/\/api\/?$/, '') + '/ws';
export const FOUND_PROMPT_DELAY_MS =
  Number(process.env.REACT_APP_FOUND_PROMPT_DELAY_MS) || 60000;
