import AsyncStorage from '@react-native-async-storage/async-storage';
import { DEFAULT_SERVER_HOST } from './config';

const STORAGE_KEY = 'avtodozor.serverHost';

let currentHost = DEFAULT_SERVER_HOST;

/**
 * Приводит введённый пользователем адрес к виду host:port.
 * «http://192.168.0.5:8000/api» -> «192.168.0.5:8000», «192.168.0.5» -> «192.168.0.5:8000».
 */
export function normalizeHost(input: string): string {
  let value = (input || '').trim();
  value = value.replace(/^[a-z]+:\/\//i, ''); // http://, ws:// ...
  value = value.split('/')[0].trim(); // отрезаем путь
  if (!value) {
    return DEFAULT_SERVER_HOST;
  }
  if (!value.includes(':')) {
    value = `${value}:8000`;
  }
  return value;
}

export function getServerHost(): string {
  return currentHost;
}

export function getApiBase(): string {
  return `http://${currentHost}/api`;
}

export function getWsUrl(employeeId: number, token: string): string {
  return `ws://${currentHost}/ws/${employeeId}?token=${encodeURIComponent(token)}`;
}

export async function loadServerHost(): Promise<string> {
  try {
    const saved = await AsyncStorage.getItem(STORAGE_KEY);
    if (saved) {
      currentHost = normalizeHost(saved);
    }
  } catch {
    // не удалось прочитать настройки: остаёмся на адресе по умолчанию
  }
  return currentHost;
}

export async function saveServerHost(input: string): Promise<string> {
  currentHost = normalizeHost(input);
  try {
    await AsyncStorage.setItem(STORAGE_KEY, currentHost);
  } catch {
    // адрес действует до закрытия приложения
  }
  return currentHost;
}
