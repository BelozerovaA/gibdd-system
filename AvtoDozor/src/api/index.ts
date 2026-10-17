import client from './client';
import { getApiBase } from '../server';
import type {
  AlertRow,
  Employee,
  ExportFormat,
  HistoryPeriod,
  LoginResponse,
  PendingAlert,
  WantedRow,
} from '../types';

// --- авторизация и профиль
export async function login(loginName: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/login', { login: loginName, password });
  return data;
}

export async function fetchProfile(): Promise<Employee> {
  const { data } = await client.get<Employee>('/employees/me');
  return data;
}

// --- розыск
export async function fetchMyWanted(): Promise<WantedRow[]> {
  const { data } = await client.get<WantedRow[]>('/wanted/my');
  return data;
}

export async function fetchAllWanted(): Promise<WantedRow[]> {
  const { data } = await client.get<WantedRow[]>('/wanted/all');
  return data;
}

export async function fetchAvailablePlates(): Promise<string[]> {
  const { data } = await client.get<string[]>('/wanted/available-plates');
  return data;
}

export async function addWanted(plate: string, reason: string): Promise<void> {
  await client.post('/wanted/add', { plate, reason });
}

export async function deleteWanted(plate: string): Promise<void> {
  await client.delete(`/wanted/${encodeURIComponent(plate)}`);
}

// --- оповещения
export async function fetchHistory(period: HistoryPeriod): Promise<AlertRow[]> {
  const { data } = await client.get<AlertRow[]>('/alerts/history', {
    params: period === 'all' ? undefined : { period },
  });
  return data;
}

export async function fetchPending(): Promise<PendingAlert[]> {
  const { data } = await client.get<PendingAlert[]>('/alerts/pending');
  return data;
}

export async function setReaction(alertId: number, status: 'Принято' | 'Отклонено'): Promise<void> {
  await client.put(`/alerts/${alertId}/reaction`, { reaction_status: status });
}

export async function setFound(alertId: number, found: 'Да' | 'Нет'): Promise<void> {
  await client.put(`/alerts/${alertId}/found`, { found_status: found });
}

/**
 * Ссылка на скачивание отчёта. Запрашивается короткоживущий токен (2 минуты),
 * потому что ссылка открывается в браузере телефона, а он не умеет слать заголовок Authorization.
 */
export async function buildExportUrl(format: ExportFormat, period: HistoryPeriod): Promise<string> {
  const { data } = await client.post<{ token: string }>('/alerts/export-token');
  const query = [`format=${format}`, `token=${encodeURIComponent(data.token)}`];
  if (period !== 'all') {
    query.push(`period=${period}`);
  }
  return `${getApiBase()}/alerts/export?${query.join('&')}`;
}
