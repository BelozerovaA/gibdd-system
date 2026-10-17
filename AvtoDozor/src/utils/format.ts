import type { HistoryPeriod } from '../types';
import { colors } from '../theme';

/** Значение или прочерк, если данных нет. */
export function orDash(value: string | null | undefined): string {
  return value && value.trim() ? value : '-';
}

/** Статус оповещения (те же правила, что в веб-интерфейсе и в выгрузке отчётов). */
export function alertStatusLabel(reaction: string | null, found: string | null): string {
  if (found === 'Да') {
    return 'Найден';
  }
  if (reaction === 'Принято') {
    return 'Принято';
  }
  if (reaction === 'Отклонено') {
    return 'Отклонено';
  }
  return 'Ожидает';
}

/** Цвет текста для статуса розыска или оповещения. */
export function statusColor(status: string): string {
  switch (status) {
    case 'В розыске':
    case 'Ожидает':
      return colors.danger;
    case 'Найден':
      return colors.success;
    case 'Принято':
      return colors.primary;
    default:
      return colors.muted;
  }
}

export const PERIODS: { label: string; value: HistoryPeriod }[] = [
  { label: 'Сегодня', value: 'today' },
  { label: 'Неделя', value: 'week' },
  { label: 'Месяц', value: 'month' },
  { label: 'Всё время', value: 'all' },
];
