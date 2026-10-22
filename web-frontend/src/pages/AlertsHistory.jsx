import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { API_URL } from '../config';
import { toast } from 'react-toastify';

export default function AlertsHistory() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('week');
  const [exportOpen, setExportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchAlerts();
  }, [period]);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/alerts/history?period=${period}`);
      setAlerts(response.data);
    } catch (error) {
      console.error('Error fetching alerts:', error);
      toast.error('Не удалось загрузить историю');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    setExporting(true);
    try {
      const { data } = await api.post('/alerts/export-token');
      const url = `${API_URL}/alerts/export?format=${format}&period=${period}&token=${encodeURIComponent(data.token)}`;
      const link = document.createElement('a');
      link.href = url;
      link.download = `alerts_history.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setExportOpen(false);
      toast.success(format === 'docx' ? 'Экспорт в Word начат' : 'Экспорт в Excel начат');
    } catch (error) {
      console.error(error);
      toast.error('Не удалось экспортировать');
    } finally {
      setExporting(false);
    }
  };

  const periods = [
    { value: 'today', label: 'Сегодня' },
    { value: 'week', label: 'Неделя' },
    { value: 'month', label: 'Месяц' },
  ];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-primary mb-4">История оповещений</h1>

      {/* Под заголовком, над таблицей: Период слева, Экспорт справа */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <span className="font-medium">Период</span>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 bg-white text-primary font-medium focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            {periods.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={() => setExportOpen(true)}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium transition"
        >
          Экспорт
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Загрузка...</div>
        ) : (
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
                    Нет оповещений за выбранный период
                  </td>
                </tr>
              ) : (
                alerts.map((alert) => (
                  <tr key={alert.id} className="border-b hover:bg-gray-50">
                    <td className="p-3 text-sm">
                      {alert.alert_date} {alert.alert_time}
                    </td>
                    <td className="p-3 font-bold">{alert.vehicle_plate}</td>
                    <td className="p-3 text-sm">{alert.address}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          alert.found_status === 'Да'
                            ? 'bg-green-500 text-white'
                            : alert.reaction_status === 'Принято'
                              ? 'bg-blue-500 text-white'
                              : alert.reaction_status === 'Отклонено'
                                ? 'bg-gray-500 text-white'
                                : 'bg-yellow-500 text-white'
                        }`}
                      >
                        {alert.found_status === 'Да'
                          ? 'Найден'
                          : alert.reaction_status === 'Принято'
                            ? 'Принято'
                            : alert.reaction_status === 'Отклонено'
                              ? 'Отклонено'
                              : 'Ожидает'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {exportOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-sm w-full overflow-hidden">
            <div className="bg-primary text-white px-6 py-4">
              <h2 className="text-lg font-bold">Экспорт истории</h2>
              <p className="text-sm text-gray-300 mt-1">
                Период: {periods.find((p) => p.value === period)?.label}
              </p>
            </div>
            <div className="p-6 space-y-3">
              <button
                type="button"
                disabled={exporting}
                onClick={() => handleExport('docx')}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-3 rounded-lg transition"
              >
                Экспорт в Word (.docx)
              </button>
              <button
                type="button"
                disabled={exporting}
                onClick={() => handleExport('xlsx')}
                className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-medium py-3 rounded-lg transition"
              >
                Экспорт в Excel (.xlsx)
              </button>
              <button
                type="button"
                disabled={exporting}
                onClick={() => setExportOpen(false)}
                className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-2 rounded-lg transition"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
