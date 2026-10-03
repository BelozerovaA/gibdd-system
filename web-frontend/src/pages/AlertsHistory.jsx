import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function AlertsHistory() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('week');

  useEffect(() => {
    fetchAlerts();
  }, [period]);

  const fetchAlerts = async () => {
    try {
      const response = await api.get(`/alerts/history?period=${period}`);
      setAlerts(response.data);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const periods = [
    { value: 'today', label: 'Сегодня' },
    { value: 'week', label: 'Неделя' },
    { value: 'month', label: 'Месяц' },
  ];

  if (loading) {
    return <div className="p-6 text-center">Загрузка...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-primary">История оповещений</h1>

        <div className="flex gap-2">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-4 py-2 rounded-lg transition ${
                period === p.value
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 hover:bg-gray-300'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-primary text-white">
            <tr>
              <th className="p-3 text-left">Дата/Время</th>
              <th className="p-3 text-left">ГРЗ</th>
              <th className="p-3 text-left">Адрес</th>
              <th className="p-3 text-left">Статус</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan="4" className="p-4 text-center text-gray-500">
                  Нет оповещений
                </td>
              </tr>
            ) : (
              alerts.map((alert, i) => (
                <tr key={i} className="border-b hover:bg-gray-50">
                  <td className="p-3 text-sm">
                    {alert.alert_date} {alert.alert_time}
                  </td>
                  <td className="p-3 font-bold">{alert.vehicle_plate}</td>
                  <td className="p-3 text-sm">{alert.address}</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      alert.found_status === 'Да' ? 'bg-green-500 text-white' :
                      alert.reaction_status === 'Принято' ? 'bg-blue-500 text-white' :
                      alert.reaction_status === 'Отклонено' ? 'bg-gray-500 text-white' :
                      'bg-yellow-500 text-white'
                    }`}>
                      {alert.found_status === 'Да' ? 'Найден' :
                       alert.reaction_status === 'Принято' ? 'Принято' :
                       alert.reaction_status === 'Отклонено' ? 'Отклонено' : 'Ожидает'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}