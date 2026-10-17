/* eslint-env jest */
import React from 'react';
import { Alert, Linking, Vibration } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import renderer, { act, ReactTestInstance, ReactTestRenderer } from 'react-test-renderer';

import App from '../App';
import { getMapImage } from '../src/assets/mapImages';
import * as api from '../src/api';

// в тесте интервалы короткие: «задержан?» через 50 мс, напоминания не мешают
jest.mock('../src/config', () => ({
  ...jest.requireActual('../src/config'),
  FOUND_PROMPT_DELAY_MS: 50,
  REMINDER_INTERVAL_MS: 600_000,
}));

jest.mock('../src/api', () => ({
  login: jest.fn(),
  fetchProfile: jest.fn(),
  fetchMyWanted: jest.fn(),
  fetchAllWanted: jest.fn(),
  fetchAvailablePlates: jest.fn(),
  addWanted: jest.fn(),
  deleteWanted: jest.fn(),
  fetchHistory: jest.fn(),
  fetchPending: jest.fn(),
  setReaction: jest.fn(),
  setFound: jest.fn(),
  buildExportUrl: jest.fn(),
}));

const mocked = api as jest.Mocked<typeof api>;

// --- поддельный WebSocket: запоминаем соединения и умеем «присылать» сообщения от сервера
class FakeSocket {
  static instances: FakeSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }
  close() {
    this.closed = true;
  }
}
(globalThis as unknown as { WebSocket: unknown }).WebSocket = FakeSocket;

// --- помощники для поиска элементов в дереве
const textOf = (node: ReactTestInstance | string): string =>
  typeof node === 'string' ? node : node.children.map(textOf).join('');

const hasText = (tree: ReactTestRenderer, text: string) =>
  tree.root.findAll(n => (n.type as unknown) === 'Text' && textOf(n).includes(text)).length > 0;

function pressable(tree: ReactTestRenderer, predicate: (n: ReactTestInstance) => boolean) {
  const found = tree.root.findAll(n => typeof n.props.onPress === 'function' && predicate(n));
  if (found.length === 0) {
    throw new Error('Нажимаемый элемент не найден');
  }
  return found[0];
}
const pressByText = async (tree: ReactTestRenderer, title: string) => {
  const node = pressable(tree, n => textOf(n) === title);
  await act(async () => {
    await node.props.onPress();
  });
};
const pressByTestId = async (tree: ReactTestRenderer, testID: string) => {
  const node = pressable(tree, n => n.props.testID === testID);
  await act(async () => {
    await node.props.onPress();
  });
};
const type = async (tree: ReactTestRenderer, testID: string, value: string) => {
  const node = tree.root.findAll(
    n => n.props.testID === testID && typeof n.props.onChangeText === 'function',
  )[0];
  await act(async () => {
    node.props.onChangeText(value);
  });
};
const isTabSelected = (tree: ReactTestRenderer, name: string) =>
  pressable(tree, n => n.props.testID === `tab-${name}`).props.accessibilityState.selected === true;
const layoutMap = async (tree: ReactTestRenderer) => {
  // на телефоне Android сам сообщает размер области карты; в тесте передаём его вручную
  const box = tree.root.findAll(
    n => n.props.testID === 'map-box' && typeof n.props.onLayout === 'function',
  )[0];
  await act(async () => {
    box.props.onLayout({ nativeEvent: { layout: { width: 360, height: 450 } } });
  });
};
const wait = (ms: number) => act(async () => new Promise<void>(r => setTimeout(r, ms)));

const PROFILE = {
  id: 1,
  login: 'ivanov_ai',
  full_name: 'Иванов Алексей Игоревич',
  birth_date: '14.03.1990',
  phone: '+7 900 000-00-00',
  email: 'ivanov@gibdd-kirov.example',
  position: 'Инспектор ДПС',
  hire_date: '01.09.2019',
  department_name: 'Управление ГИБДД по Кировской области',
  is_active: true,
};

const WANTED_ROW = {
  id: 1,
  plate: 'А111АА43',
  model: 'Lada Vesta',
  color: 'Белый',
  status: 'В розыске',
  fix_time: '10:00:00',
  fix_date: '01.10.2026',
  fix_address: 'ул. Московская 106/1',
  employee_name: 'Иванов Алексей Игоревич',
  reaction_status: 'Ожидает',
  found_status: 'Нет',
};

let tree: ReactTestRenderer;
let alertSpy: jest.SpyInstance;

async function renderApp() {
  await act(async () => {
    tree = renderer.create(<App />);
  });
  await wait(10);
}

async function loginAsIvanov() {
  await type(tree, 'login-input', 'ivanov_ai');
  await type(tree, 'password-input', 'Ivanov2024');
  await pressByText(tree, 'Войти');
  await wait(10);
}

beforeEach(async () => {
  await AsyncStorage.clear();
  FakeSocket.instances = [];
  jest.clearAllMocks();
  jest.spyOn(Vibration, 'vibrate').mockImplementation(() => {});
  alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => {});

  mocked.login.mockResolvedValue({
    access_token: 'tok-abc',
    token_type: 'bearer',
    user_id: 1,
    full_name: PROFILE.full_name,
    position: 'Инспектор ДПС',
    email: PROFILE.email,
  });
  mocked.fetchProfile.mockResolvedValue(PROFILE);
  mocked.fetchMyWanted.mockResolvedValue([WANTED_ROW]);
  mocked.fetchAllWanted.mockResolvedValue([
    WANTED_ROW,
    { ...WANTED_ROW, id: 2, plate: 'В222ВВ43', employee_name: 'Петрова Елена Андреевна' },
  ]);
  mocked.fetchAvailablePlates.mockResolvedValue(['Е333ЕЕ43', 'К444КК43']);
  mocked.fetchHistory.mockResolvedValue([
    {
      id: 5,
      vehicle_plate: 'А111АА43',
      alert_date: '03.10.2026',
      alert_time: '12:00:00',
      address: 'ул. Московская 106/1',
      camera_id: 8,
      reaction_status: 'Принято',
      found_status: 'Нет',
      wanted_status: 'В розыске',
      is_viewed: true,
    },
  ]);
  mocked.fetchPending.mockResolvedValue([]);
  mocked.setReaction.mockResolvedValue();
  mocked.setFound.mockResolvedValue();
  mocked.addWanted.mockResolvedValue();
  mocked.deleteWanted.mockResolvedValue();
  mocked.buildExportUrl.mockResolvedValue('http://10.0.2.2:8000/api/alerts/export?format=docx&token=t');
});

afterEach(async () => {
  await act(async () => {
    tree?.unmount();
  });
  jest.restoreAllMocks();
});

describe('Авторизация (ТЗ, рисунок 1)', () => {
  it('до входа видна форма входа и нет кнопок меню', async () => {
    await renderApp();
    expect(hasText(tree, 'Вход в систему оперативного розыска транспортных средств')).toBe(true);
    expect(tree.root.findAll(n => n.props.testID === 'tab-Profile')).toHaveLength(0);
  });

  it('пустые поля: показывает подсказку и не обращается к серверу', async () => {
    await renderApp();
    await pressByText(tree, 'Войти');
    expect(hasText(tree, 'Введите логин и пароль')).toBe(true);
    expect(mocked.login).not.toHaveBeenCalled();
  });

  it('неверный пароль: показывает сообщение сервера и остаётся на входе', async () => {
    const err = Object.assign(new Error('x'), {
      isAxiosError: true,
      response: { status: 401, data: { detail: 'Неверный логин или пароль' } },
    });
    mocked.login.mockRejectedValueOnce(err);
    await renderApp();
    await type(tree, 'login-input', 'ivanov_ai');
    await type(tree, 'password-input', 'wrong');
    await pressByText(tree, 'Войти');
    await wait(10);
    expect(hasText(tree, 'Неверный логин или пароль')).toBe(true);
    expect(hasText(tree, 'Вход в систему')).toBe(true);
  });

  it('успешный вход: открывается личный кабинет и устанавливается WebSocket', async () => {
    await renderApp();
    await loginAsIvanov();

    expect(mocked.login).toHaveBeenCalledWith('ivanov_ai', 'Ivanov2024');
    expect(hasText(tree, 'Личный кабинет')).toBe(true);
    expect(hasText(tree, 'Иванов Алексей Игоревич')).toBe(true);
    expect(hasText(tree, '14.03.1990')).toBe(true);
    expect(hasText(tree, 'Управление ГИБДД по Кировской области')).toBe(true);
    expect(isTabSelected(tree, 'Profile')).toBe(true);

    // симулятора в backend больше нет: оповещения создаёт сервис ГИБДД по событиям от сервиса камер
    expect(Object.keys(mocked).some(name => /simulator/i.test(name))).toBe(false);
    expect(FakeSocket.instances).toHaveLength(1);
    expect(FakeSocket.instances[0].url).toBe('ws://10.0.2.2:8000/ws/1?token=tok-abc');
  });
});

describe('Меню навигации', () => {
  it('пять кнопок, активная выделена; переходы работают', async () => {
    await renderApp();
    await loginAsIvanov();

    for (const label of ['Личный кабинет', 'Мой розыск', 'База розыска', 'Карта', 'История оповещений']) {
      expect(hasText(tree, label)).toBe(true);
    }
    const tabs: [string, string][] = [
      ['MyWanted', 'Мой розыск'],
      ['AllWanted', 'База розыска'],
      ['Map', 'Карта'],
      ['History', 'История оповещений'],
      ['Profile', 'Личный кабинет'],
    ];
    for (const [name] of tabs) {
      await pressByTestId(tree, `tab-${name}`);
      await wait(5);
      expect(isTabSelected(tree, name)).toBe(true);
    }
  });
});

describe('Оповещение (ТЗ, рисунки 6-8)', () => {
  const detection = {
    type: 'detection',
    alert_id: 77,
    wanted_id: 1,
    plate: 'А111АА43',
    camera_id: 8,
    camera_number: 8,
    address: 'ул. Московская 106/1',
    latitude: 58.6,
    longitude: 49.65,
    date: '03.10.2026',
    time: '12:00:00',
  };

  it('тревога: окно, переход на карту, подсветка камеры; «Принять» -> вопрос -> «Да»', async () => {
    await renderApp();
    await loginAsIvanov();

    // сервер присылает оповещение
    await act(async () => {
      FakeSocket.instances[0].onmessage?.({ data: JSON.stringify(detection) });
    });

    // окно с ГРЗ, местом, временем и датой
    expect(hasText(tree, 'Оповещение')).toBe(true);
    expect(hasText(tree, 'А111АА43')).toBe(true);
    expect(hasText(tree, 'ул. Московская 106/1')).toBe(true);
    expect(hasText(tree, '12:00:00')).toBe(true);
    expect(hasText(tree, '03.10.2026')).toBe(true);
    expect(Vibration.vibrate).toHaveBeenCalled();

    // карта переключилась на сработавшую камеру
    expect(isTabSelected(tree, 'Map')).toBe(true);
    await layoutMap(tree);
    const image = tree.root.findAll(n => n.props.testID === 'map-image' && n.props.source)[0];
    expect(image.props.source).toBe(getMapImage(8));
    expect(hasText(tree, 'зафиксирован на камере №8')).toBe(true);

    // «Принять»: факт получения фиксируется, окно закрывается
    await pressByText(tree, 'Принять');
    expect(mocked.setReaction).toHaveBeenCalledWith(77, 'Принято');
    expect(hasText(tree, 'Принять')).toBe(false);

    // через интервал спрашивает о результате
    await wait(80);
    expect(hasText(tree, 'Результат розыска')).toBe(true);
    expect(hasText(tree, 'А111АА43 задержан?')).toBe(true);

    // «Да»: статус меняется, карта возвращается к общей
    await pressByText(tree, 'Да');
    expect(mocked.setFound).toHaveBeenCalledWith(77, 'Да');
    expect(hasText(tree, 'Результат розыска')).toBe(false);
    const imageAfter = tree.root.findAll(n => n.props.testID === 'map-image' && n.props.source)[0];
    expect(imageAfter.props.source).toBe(getMapImage(null));
  });

  it('«Нет»: розыск продолжается', async () => {
    await renderApp();
    await loginAsIvanov();
    await act(async () => {
      FakeSocket.instances[0].onmessage?.({ data: JSON.stringify(detection) });
    });
    await pressByText(tree, 'Принять');
    await wait(80);
    await pressByText(tree, 'Нет');
    expect(mocked.setFound).toHaveBeenCalledWith(77, 'Нет');
  });

  it('ошибка сервера при «Принять»: окно остаётся открытым, можно повторить', async () => {
    mocked.setReaction.mockRejectedValueOnce(new Error('сеть'));
    await renderApp();
    await loginAsIvanov();
    await act(async () => {
      FakeSocket.instances[0].onmessage?.({ data: JSON.stringify(detection) });
    });
    await pressByText(tree, 'Принять');
    expect(hasText(tree, 'Принять')).toBe(true); // окно не закрылось
    await pressByText(tree, 'Принять');
    expect(mocked.setReaction).toHaveBeenCalledTimes(2);
    expect(hasText(tree, 'Принять')).toBe(false);
  });

  it('повторное оповещение: неотвеченное оповещение показывается снова', async () => {
    mocked.fetchPending.mockResolvedValue([
      { id: 31, plate: 'В222ВВ43', address: 'ул. Ленина 1', date: '03.10.2026', time: '09:00:00' },
    ]);
    await renderApp();
    await loginAsIvanov();
    expect(hasText(tree, 'В222ВВ43')).toBe(false);
    await wait(3300); // первая проверка неотвеченных оповещений идёт через 3 секунды после входа
    expect(mocked.fetchPending).toHaveBeenCalled();
    expect(hasText(tree, 'В222ВВ43')).toBe(true);
    expect(hasText(tree, 'ул. Ленина 1')).toBe(true);
    // по напоминанию карта не переключается: номер камеры неизвестен
    expect(isTabSelected(tree, 'Profile')).toBe(true);
    await pressByText(tree, 'Принять');
    expect(mocked.setReaction).toHaveBeenCalledWith(31, 'Принято');
  }, 15000);
});

describe('Мой розыск (ТЗ, рисунки 3-4)', () => {
  it('таблица со всеми столбцами, добавление и удаление записей', async () => {
    await renderApp();
    await loginAsIvanov();
    await pressByTestId(tree, 'tab-MyWanted');
    await wait(10);

    for (const col of ['ГРЗ', 'Статус', 'Модель', 'Цвет', 'Время', 'Дата', 'Адрес']) {
      expect(hasText(tree, col)).toBe(true);
    }
    expect(hasText(tree, 'А111АА43')).toBe(true);
    expect(hasText(tree, 'Lada Vesta')).toBe(true);

    // удаление без выбора строки
    await pressByText(tree, 'Удалить из розыска');
    expect(mocked.deleteWanted).not.toHaveBeenCalled();

    // выбор строки -> подтверждение -> «Да»
    await pressByTestId(tree, 'row-1');
    await pressByText(tree, 'Удалить из розыска');
    expect(alertSpy).toHaveBeenCalled();
    const buttons = alertSpy.mock.calls[alertSpy.mock.calls.length - 1][2] as {
      text: string;
      onPress?: () => Promise<void>;
    }[];
    expect(buttons.map(b => b.text)).toEqual(['Отмена', 'Да']);
    await act(async () => {
      await buttons[1].onPress?.();
    });
    expect(mocked.deleteWanted).toHaveBeenCalledWith('А111АА43');

    // добавление: открывается диалог со списком ГРЗ
    await pressByText(tree, 'Добавить в розыск');
    await wait(10);
    expect(mocked.fetchAvailablePlates).toHaveBeenCalled();
    expect(hasText(tree, 'Добавление данных')).toBe(true);
    await pressByText(tree, 'Добавить');
    await wait(10);
    expect(mocked.addWanted).toHaveBeenCalledWith('Е333ЕЕ43', expect.any(String));
    expect(hasText(tree, 'Добавление данных')).toBe(false);

    // «Отмена» закрывает диалог без добавления
    mocked.addWanted.mockClear();
    await pressByText(tree, 'Добавить в розыск');
    await wait(10);
    await pressByText(tree, 'Отмена');
    expect(hasText(tree, 'Добавление данных')).toBe(false);
    expect(mocked.addWanted).not.toHaveBeenCalled();
  });
});

describe('База розыска (ТЗ, рисунок 5)', () => {
  it('показывает записи всех сотрудников, без кнопок добавления и удаления', async () => {
    await renderApp();
    await loginAsIvanov();
    await pressByTestId(tree, 'tab-AllWanted');
    await wait(10);

    for (const col of ['ГРЗ', 'Статус', 'Цвет', 'Сотрудник', 'Время', 'Дата', 'Адрес']) {
      expect(hasText(tree, col)).toBe(true);
    }
    expect(hasText(tree, 'В222ВВ43')).toBe(true);
    expect(hasText(tree, 'Петрова Елена Андреевна')).toBe(true);
    expect(hasText(tree, 'Добавить в розыск')).toBe(false);
    expect(hasText(tree, 'Удалить из розыска')).toBe(false);
  });
});

describe('Карта (ТЗ, рисунок 6)', () => {
  it('кнопки масштаба работают и ограничены', async () => {
    await renderApp();
    await loginAsIvanov();
    await pressByTestId(tree, 'tab-Map');
    await wait(10);

    const label = () => textOf(tree.root.findAll(n => n.props.testID === 'zoom-label')[0]);
    expect(label()).toBe('100%');
    await pressByText(tree, 'Увеличить +');
    expect(label()).toBe('150%');
    await pressByText(tree, 'Уменьшить −');
    await pressByText(tree, 'Уменьшить −');
    expect(label()).toBe('50%');
    // на минимуме кнопка «Уменьшить» отключена
    const minus = pressable(tree, n => textOf(n) === 'Уменьшить −');
    expect(minus.props.disabled).toBe(true);
  });
});

describe('История оповещений (ТЗ, рисунки 9-10)', () => {
  it('период, «Обновить» и «Экспорт» с выбором формата', async () => {
    jest.spyOn(Linking, 'openURL').mockResolvedValue(undefined);
    await renderApp();
    await loginAsIvanov();
    await pressByTestId(tree, 'tab-History');
    await wait(10);

    expect(hasText(tree, 'А111АА43')).toBe(true);
    expect(mocked.fetchHistory).toHaveBeenCalledWith('today');

    // смена периода
    const picker = tree.root.findAll(
      n => n.props.testID === 'period-picker' && typeof n.props.onValueChange === 'function',
    )[0];
    await act(async () => {
      picker.props.onValueChange('week');
    });
    await wait(10);
    expect(mocked.fetchHistory).toHaveBeenCalledWith('week');

    // «Обновить» перезагружает таблицу
    mocked.fetchHistory.mockClear();
    await pressByText(tree, 'Обновить');
    await wait(10);
    expect(mocked.fetchHistory).toHaveBeenCalledWith('week');

    // «Экспорт» -> диалог выбора формата
    await pressByText(tree, 'Экспорт');
    expect(hasText(tree, 'В каком формате сохранить отчёт?')).toBe(true);
    await pressByText(tree, 'Word (docx)');
    await wait(10);
    expect(mocked.buildExportUrl).toHaveBeenCalledWith('docx', 'week');
    expect(Linking.openURL).toHaveBeenCalledWith(
      'http://10.0.2.2:8000/api/alerts/export?format=docx&token=t',
    );
    expect(hasText(tree, 'В каком формате сохранить отчёт?')).toBe(false);

    // Excel и «Отмена»
    await pressByText(tree, 'Экспорт');
    await pressByText(tree, 'Excel (xlsx)');
    await wait(10);
    expect(mocked.buildExportUrl).toHaveBeenLastCalledWith('xlsx', 'week');
    await pressByText(tree, 'Экспорт');
    await pressByText(tree, 'Отмена');
    expect(hasText(tree, 'В каком формате сохранить отчёт?')).toBe(false);
  });
});

describe('Выход', () => {
  it('«Выйти из системы» возвращает на вход и закрывает WebSocket', async () => {
    await renderApp();
    await loginAsIvanov();
    await pressByText(tree, 'Выйти из системы');
    await wait(10);
    expect(hasText(tree, 'Вход в систему оперативного розыска транспортных средств')).toBe(true);
    expect(FakeSocket.instances[0].closed).toBe(true);
  });
});
