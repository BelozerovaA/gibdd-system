import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import api from '../services/api';
import { WS_URL, FOUND_PROMPT_DELAY_MS } from '../config';

const AlertContext = createContext(null);

export function useAlerts() {
  return useContext(AlertContext);
}

export function AlertProvider({ children }) {
  const { user, token } = useSelector((state) => state.auth);
  const navigate = useNavigate();
  const wsRef = useRef(null);
  const foundTimerRef = useRef(null);

  const [detection, setDetection] = useState(null);
  const [askFound, setAskFound] = useState(null);
  const [highlight, setHighlight] = useState(null);

  useEffect(() => {
    if (!user?.id || !token) return;

    api.post('/simulator/start').catch(() => {});

    const ws = new WebSocket(`${WS_URL}/${user.id}?token=${token}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'detection') {
          setDetection(data);
          setHighlight({
            camera: data.camera_number ?? data.camera_id,
            address: data.address,
            plate: data.plate,
          });
          navigate('/map');
        }
      } catch (e) {
      }
    };

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
    }, 25000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [user?.id, token]);

  const acceptDetection = useCallback(async () => {
    if (!detection) return;
    try {
      await api.put(`/alerts/${detection.alert_id}/reaction`, { reaction_status: 'Принято' });
    } catch (e) {
      // окно остаётся открытым, чтобы можно было повторить: иначе оповещение
      // осталось бы на сервере без реакции, хотя сотрудник считает его принятым
      toast.error('Не удалось отправить подтверждение, попробуйте ещё раз');
      return;
    }
    const payload = detection;
    setDetection(null);
    foundTimerRef.current = setTimeout(() => setAskFound(payload), FOUND_PROMPT_DELAY_MS);
  }, [detection]);

  const answerFound = useCallback(async (foundYes) => {
    if (!askFound) return;
    try {
      await api.put(`/alerts/${askFound.alert_id}/found`, {
        found_status: foundYes ? 'Да' : 'Нет',
      });
      toast[foundYes ? 'success' : 'info'](
        foundYes ? `Автомобиль ${askFound.plate} задержан` : `Автомобиль ${askFound.plate} не найден, розыск продолжается`
      );
    } catch (e) {
      toast.error('Не удалось обновить статус');
    }
    setAskFound(null);
    try {
      await api.post('/simulator/resume');
    } catch (e) {
    }
  }, [askFound]);

  const clearHighlight = useCallback(() => setHighlight(null), []);

  useEffect(() => () => {
    if (foundTimerRef.current) clearTimeout(foundTimerRef.current);
  }, []);

  const value = {
    detection,
    askFound,
    highlight,
    clearHighlight,
    acceptDetection,
    answerFound,
  };

  return <AlertContext.Provider value={value}>{children}</AlertContext.Provider>;
}
