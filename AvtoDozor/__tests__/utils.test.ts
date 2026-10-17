import { getMapImage } from '../src/assets/mapImages';
import { getErrorMessage } from '../src/api/client';
import { DEFAULT_SERVER_HOST } from '../src/config';
import { normalizeHost } from '../src/server';
import { alertStatusLabel, orDash, statusColor } from '../src/utils/format';
import { colors } from '../src/theme';

describe('normalizeHost', () => {
  it('убирает протокол и путь', () => {
    expect(normalizeHost('http://192.168.0.5:8000/api')).toBe('192.168.0.5:8000');
    expect(normalizeHost('ws://10.0.2.2:8000/ws')).toBe('10.0.2.2:8000');
  });
  it('добавляет порт 8000, если его нет', () => {
    expect(normalizeHost('192.168.0.5')).toBe('192.168.0.5:8000');
  });
  it('пустой ввод даёт адрес по умолчанию', () => {
    expect(normalizeHost('   ')).toBe(DEFAULT_SERVER_HOST);
  });
  it('обрезает пробелы', () => {
    expect(normalizeHost('  192.168.1.2:9000 ')).toBe('192.168.1.2:9000');
  });
});

describe('alertStatusLabel', () => {
  it('те же правила, что в вебе и в отчётах', () => {
    expect(alertStatusLabel('Ожидает', 'Да')).toBe('Найден');
    expect(alertStatusLabel('Принято', 'Нет')).toBe('Принято');
    expect(alertStatusLabel('Отклонено', 'Нет')).toBe('Отклонено');
    expect(alertStatusLabel(null, null)).toBe('Ожидает');
  });
  it('цвета статусов', () => {
    expect(statusColor('В розыске')).toBe(colors.danger);
    expect(statusColor('Найден')).toBe(colors.success);
    expect(statusColor('Передан')).toBe(colors.muted);
  });
});

describe('orDash', () => {
  it('подставляет прочерк вместо пустого значения', () => {
    expect(orDash(null)).toBe('-');
    expect(orDash('  ')).toBe('-');
    expect(orDash('Lada')).toBe('Lada');
  });
});

describe('getMapImage', () => {
  it('для каждой камеры 1-15 своя картинка, отличная от общей карты', () => {
    const general = getMapImage(null);
    const seen = new Set<unknown>();
    for (let n = 1; n <= 15; n++) {
      const img = getMapImage(n);
      expect(img).not.toBe(general);
      seen.add(img);
    }
    expect(seen.size).toBe(15);
  });
  it('для неизвестного номера возвращает общую карту', () => {
    expect(getMapImage(99)).toBe(getMapImage(undefined));
  });
});

describe('getErrorMessage', () => {
  it('берёт текст detail из ответа сервера', () => {
    const err = { isAxiosError: true, response: { status: 400, data: { detail: 'Автомобиль уже в розыске' } } };
    expect(getErrorMessage(err)).toBe('Автомобиль уже в розыске');
  });
  it('сообщает об отсутствии связи', () => {
    const err = { isAxiosError: true, response: undefined, code: 'ERR_NETWORK' };
    expect(getErrorMessage(err)).toMatch(/Нет связи с сервером/);
  });
  it('для 422 без текста показывает код', () => {
    const err = { isAxiosError: true, response: { status: 422, data: { detail: [{ msg: 'x' }] } } };
    expect(getErrorMessage(err)).toBe('Ошибка сервера (422)');
  });
});
