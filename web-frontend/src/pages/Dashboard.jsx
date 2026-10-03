import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { toast } from 'react-toastify';
import {
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  MapPinIcon,
  BellIcon,
  XMarkIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

export default function Dashboard() {
  const { user, token } = useSelector((state) => state.auth);
  const [stats, setStats] = useState({ total: 0, active: 0, found: 0 });
  const [pendingAlerts, setPendingAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
    // Poll for new alerts every 30 seconds
    const interval = setInterval(fetchPendingAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      await Promise.all([fetchStats(), fetchPendingAlerts()]);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/wanted/my');
      const vehicles = response.data;
      setStats({
        total: vehicles.length,
        active: vehicles.filter(v => v.status === 'В розыске').length,
        found: vehicles.filter(v => v.status === 'Найден').length,
      });
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchPendingAlerts = async () => {
    try {
      const response = await api.get('/alerts/pending');
      setPendingAlerts(response.data);
    } catch (error) {
      console.error('Error fetching pending alerts:', error);
    }
  };

  const handleAlertReaction = async (alertId, status) => {
    try {
      await api.put(`/alerts/${alertId}/reaction`, { reaction_status: status });
      toast.success('Статус обновлен');
      // Сотрудник отреагировал на оповещение здесь, а не в окне поверх карты:
      // снимаем паузу, чтобы симулятор продолжил искать машины.
      api.post('/simulator/resume').catch(() => {});
      fetchPendingAlerts();
      fetchStats();
    } catch (error) {
      toast.error('Ошибка обновления статуса');
    }
  };

  const statCards = [
    { label: 'В розыске', value: stats.active, color: 'bg-danger', icon: ExclamationTriangleIcon },
    { label: 'Найдено', value: stats.found, color: 'bg-success', icon: CheckCircleIcon },
    { label: 'Всего', value: stats.total, color: 'bg-secondary', icon: ShieldCheckIcon },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-secondary"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary">Панель управления</h1>
        <p className="text-gray-500">Добро пожаловать, {user?.full_name}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {statCards.map((stat) => (
          <div key={stat.label} className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">{stat.label}</p>
                <p className="text-3xl font-bold">{stat.value}</p>
              </div>
              <div className={`${stat.color} p-3 rounded-full`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pending Alerts */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-primary flex items-center">
            <BellIcon className="w-6 h-6 mr-2 text-warning" />
            Активные оповещения
          </h2>
          {pendingAlerts.length > 0 && (
            <span className="bg-danger text-white text-xs px-2 py-1 rounded-full">
              {pendingAlerts.length} новых
            </span>
          )}
        </div>

        {pendingAlerts.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-400">Нет активных оповещений</p>
          </div>
        ) : (
          <div className="space-y-3">
            {pendingAlerts.map((alert) => (
              <div
                key={alert.id}
                className="border-l-4 border-warning bg-warning/5 p-4 rounded-r-lg flex items-center justify-between"
              >
                <div>
                  <p className="font-bold text-lg">{alert.plate}</p>
                  <p className="text-sm text-gray-600">
                    <MapPinIcon className="w-4 h-4 inline mr-1" />
                    {alert.address}
                  </p>
                  <p className="text-xs text-gray-400">
                    {alert.date} {alert.time}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleAlertReaction(alert.id, 'Принято')}
                    className="bg-success hover:bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
                  >
                    Принято
                  </button>
                  <button
                    onClick={() => handleAlertReaction(alert.id, 'Отклонено')}
                    className="bg-gray-400 hover:bg-gray-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
                  >
                    Отклонить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}