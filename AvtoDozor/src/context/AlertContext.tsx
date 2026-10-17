import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { AppState, Vibration } from 'react-native';
import * as api from '../api';
import { getErrorMessage } from '../api/client';
import { FOUND_PROMPT_DELAY_MS, REMINDER_INTERVAL_MS } from '../config';
import { navigationRef } from '../navigation/navigationRef';
import { getWsUrl } from '../server';
import type { DetectionPayload } from '../types';
import { notify } from '../utils/notify';
import { useAuth } from './AuthContext';
import DetectionModal from '../components/DetectionModal';
import FoundModal from '../components/FoundModal';

export interface Highlight {
  camera: number;
  address: string;
  plate: string;
}

interface AlertContextValue {
  /** Камера, на которой только что зафиксирован автомобиль (карта показывает её выделенной). */
  highlight: Highlight | null;
  clearHighlight: () => void;
}

const AlertContext = createContext<AlertContextValue | null>(null);

interface FoundQuestion {
  alertId: number;
  plate: string;
}

export function AlertProvider({ children }: { children: React.ReactNode }) {
  const { user, token } = useAuth();

  const [detection, setDetection] = useState<DetectionPayload | null>(null);
  const [foundQuestion, setFoundQuestion] = useState<FoundQuestion | null>(null);
  const [highlight, setHighlight] = useState<Highlight | null>(null);
  const [busy, setBusy] = useState(false);

  // актуальные значения для колбэков WebSocket и таймеров
  const detectionRef = useRef<DetectionPayload | null>(null);
  const foundRef = useRef<FoundQuestion | null>(null);
  const waitingForFoundRef = useRef<Set<number>>(new Set());
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  detectionRef.current = detection;
  foundRef.current = foundQuestion;

  const showDetection = useCallback((payload: DetectionPayload, goToMap: boolean) => {
    if (detectionRef.current || foundRef.current) {
      return; // уже открыто окно: не накладываем второе
    }
    if (waitingForFoundRef.current.has(payload.alert_id)) {
      return; // на это оповещение уже ответили «Принять», ждём вопрос о результате
    }
    setDetection(payload);
    if (payload.camera_number != null) {
      setHighlight({
        camera: payload.camera_number,
        address: payload.address,
        plate: payload.plate,
      });
    }
    Vibration.vibrate([0, 400, 200, 400]);
    if (goToMap && navigationRef.isReady()) {
      // по ТЗ при тревоге карта автоматически переключается на сработавшую камеру
      navigationRef.navigate('Main', { screen: 'Map' });
    }
  }, []);

  // --- приём оповещений по WebSocket (их создаёт сервис ГИБДД по событиям от сервиса камер)
  useEffect(() => {
    if (!user || !token) {
      return undefined;
    }

    let closedByUs = false;
    let attempt = 0;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      socket = new WebSocket(getWsUrl(user.id, token));
      socket.onopen = () => {
        attempt = 0;
      };
      socket.onmessage = event => {
        try {
          const data = JSON.parse(String(event.data));
          if (data.type === 'detection') {
            showDetection(
              {
                alert_id: data.alert_id,
                plate: data.plate,
                address: data.address,
                date: data.date,
                time: data.time,
                camera_number: data.camera_number ?? data.camera_id ?? null,
              },
              true,
            );
          }
        } catch {
          // чужое или повреждённое сообщение: пропускаем
        }
      };
      socket.onerror = () => {
        // подробности придут в onclose, где мы переподключаемся
      };
      socket.onclose = () => {
        if (closedByUs) {
          return;
        }
        const delay = Math.min(1000 * 2 ** attempt, 10_000);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };
    connect();

    return () => {
      closedByUs = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [user, token, showDetection]);

  // --- повторное оповещение, если сотрудник не ответил (ТЗ: «повторно отправить оповещение»)
  useEffect(() => {
    if (!user || !token) {
      return undefined;
    }

    const check = async () => {
      if (detectionRef.current || foundRef.current) {
        return;
      }
      try {
        const pending = await api.fetchPending();
        if (pending.length === 0) {
          return;
        }
        const oldest = pending[pending.length - 1]; // сервер отдаёт от новых к старым
        showDetection(
          {
            alert_id: oldest.id,
            plate: oldest.plate,
            address: oldest.address,
            date: oldest.date,
            time: oldest.time,
            camera_number: null,
          },
          false,
        );
      } catch {
        // сервер недоступен: попробуем в следующий раз
      }
    };

    const first = setTimeout(check, 3000);
    const interval = setInterval(check, REMINDER_INTERVAL_MS);
    const appStateSub = AppState.addEventListener('change', state => {
      if (state === 'active') {
        check();
      }
    });

    return () => {
      clearTimeout(first);
      clearInterval(interval);
      appStateSub.remove();
    };
  }, [user, token, showDetection]);

  // выход из системы: сбрасываем всё состояние
  useEffect(() => {
    if (!user) {
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
      waitingForFoundRef.current.clear();
      setDetection(null);
      setFoundQuestion(null);
      setHighlight(null);
      setBusy(false);
    }
  }, [user]);

  useEffect(
    () => () => {
      timersRef.current.forEach(clearTimeout);
    },
    [],
  );

  const accept = useCallback(async () => {
    const current = detectionRef.current;
    if (!current || busy) {
      return;
    }
    setBusy(true);
    try {
      await api.setReaction(current.alert_id, 'Принято');
    } catch (error) {
      notify(getErrorMessage(error), true);
      setBusy(false);
      return; // окно остаётся открытым: можно нажать «Принять» ещё раз
    }
    setBusy(false);
    setDetection(null);

    // через заданный интервал спрашиваем о результате (ТЗ, рисунок 8)
    waitingForFoundRef.current.add(current.alert_id);
    const timer = setTimeout(() => {
      waitingForFoundRef.current.delete(current.alert_id);
      setFoundQuestion({ alertId: current.alert_id, plate: current.plate });
    }, FOUND_PROMPT_DELAY_MS);
    timersRef.current.push(timer);
  }, [busy]);

  const answerFound = useCallback(
    async (found: 'Да' | 'Нет') => {
      const current = foundRef.current;
      if (!current || busy) {
        return;
      }
      setBusy(true);
      try {
        await api.setFound(current.alertId, found);
      } catch (error) {
        notify(getErrorMessage(error), true);
        setBusy(false);
        return;
      }
      setBusy(false);
      setFoundQuestion(null);
      setHighlight(null);
      notify(
        found === 'Да'
          ? 'Автомобиль исключён из активного розыска'
          : 'Розыск продолжается',
      );
    },
    [busy],
  );

  const clearHighlight = useCallback(() => setHighlight(null), []);

  const value = useMemo(() => ({ highlight, clearHighlight }), [highlight, clearHighlight]);

  return (
    <AlertContext.Provider value={value}>
      {children}
      <DetectionModal detection={detection} busy={busy} onAccept={accept} />
      <FoundModal question={foundQuestion} busy={busy} onAnswer={answerFound} />
    </AlertContext.Provider>
  );
}

export function useAlerts(): AlertContextValue {
  const ctx = useContext(AlertContext);
  if (!ctx) {
    throw new Error('useAlerts нужно вызывать внутри AlertProvider');
  }
  return ctx;
}
