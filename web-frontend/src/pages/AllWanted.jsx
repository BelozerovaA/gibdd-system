import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import api from '../services/api';
import { toast } from 'react-toastify';

export default function AllWanted() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useSelector((state) => state.auth);

  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    try {
      const response = await api.get('/wanted/all');
      setVehicles(response.data);
    } catch (error) {
      console.error('Error fetching vehicles:', error);
      toast.error('Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  };

  const handleTake = async (wantedId, plate) => {
    if (!window.confirm(`Взять автомобиль ${plate} в свой розыск?`)) return;

    try {
      await api.post(`/wanted/take/${wantedId}`);
      toast.success(`Автомобиль ${plate} взят в розыск`);
      fetchVehicles();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка');
    }
  };

  if (loading) {
    return <div className="p-6 text-center">Загрузка...</div>;
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-primary">База розыска</h1>
        <p className="text-sm text-gray-500 mt-1">
          Все автомобили в розыске у всех сотрудников. Всего: {vehicles.length}
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-primary text-white">
            <tr>
              <th className="p-3 text-left">ГРЗ</th>
              <th className="p-3 text-left">Модель</th>
              <th className="p-3 text-left">Цвет</th>
              <th className="p-3 text-left">Сотрудник</th>
              <th className="p-3 text-left">Статус</th>
              <th className="p-3 text-left">Действие</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.length === 0 ? (
              <tr>
                <td colSpan="6" className="p-4 text-center text-gray-500">
                  Нет автомобилей в розыске
                </td>
              </tr>
            ) : (
              vehicles.map((v) => {
                const isMyWanted = v.employee_name === user?.full_name;

                return (
                  <tr key={v.id} className="border-b hover:bg-gray-50">
                    <td className="p-3 font-bold">{v.plate}</td>
                    <td className="p-3">{v.model || '-'}</td>
                    <td className="p-3">{v.color || '-'}</td>
                    <td className="p-3">
                      <span className={isMyWanted ? 'font-bold text-blue-600' : ''}>
                        {v.employee_name || '-'}
                        {isMyWanted && ' (Вы)'}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        v.status === 'В розыске' ? 'bg-red-500 text-white' :
                        v.status === 'Найден' ? 'bg-green-500 text-white' :
                        'bg-gray-500 text-white'
                      }`}>
                        {v.status}
                      </span>
                    </td>
                    <td className="p-3">
                      {!isMyWanted && v.status === 'В розыске' ? (
                        <button
                          onClick={() => handleTake(v.id, v.plate)}
                          className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium transition"
                        >
                          Взять себе
                        </button>
                      ) : isMyWanted ? (
                        <span className="text-gray-400 text-sm">Это ваш розыск</span>
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}