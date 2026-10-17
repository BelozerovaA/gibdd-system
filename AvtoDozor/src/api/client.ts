import axios, { AxiosError } from 'axios';
import { REQUEST_TIMEOUT_MS } from '../config';
import { getApiBase } from '../server';

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

/** Вызывается, когда сервер ответил 401 на запрос с токеном (токен истёк). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

const client = axios.create({
  timeout: REQUEST_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use(config => {
  // адрес читаем при каждом запросе: его можно сменить в настройках без перезапуска
  config.baseURL = getApiBase();
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

client.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && authToken && onUnauthorized) {
      onUnauthorized();
    }
    return Promise.reject(error);
  },
);

/** Человекочитаемый текст ошибки запроса. */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      const detail = (error.response.data as { detail?: unknown } | undefined)?.detail;
      if (typeof detail === 'string' && detail) {
        return detail;
      }
      return `Ошибка сервера (${error.response.status})`;
    }
    if (error.code === 'ECONNABORTED') {
      return 'Сервер не отвечает. Попробуйте ещё раз';
    }
    return 'Нет связи с сервером. Проверьте адрес сервера и подключение';
  }
  return 'Произошла непредвиденная ошибка';
}

export default client;
