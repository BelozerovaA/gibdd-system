import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { toast } from 'react-toastify';

export default function MyWanted() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlate, setSelectedPlate] = useState(null);
  const [addStep, setAddStep] = useState(0);
  const [availablePlates, setAvailablePlates] = useState([]);
  const [violationCategories, setViolationCategories] = useState([]);
  const [chosenPlate, setChosenPlate] = useState('');
  const [chosenReason, setChosenReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    try {
      const response = await api.get('/wanted/my');
      setVehicles(response.data);
    } catch (error) {
      toast.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const openAddDialog = async () => {
    try {
      const [platesRes, categoriesRes] = await Promise.all([
        api.get('/wanted/available-plates'),
        api.get('/wanted/violation-categories'),
      ]);
      if (platesRes.data.length === 0) {
        toast.info('Все автомобили в базе уже находятся в розыске');
        return;
      }
      setAvailablePlates(platesRes.data);
      setViolationCategories(categoriesRes.data);
      setChosenPlate(platesRes.data[0]);
      setChosenReason(categoriesRes.data[0] || '');
      setAddStep(1);
    } catch (error) {
      toast.error('Не удалось загрузить список автомобилей');
    }
  };

  const goToReasonStep = () => setAddStep(2);

  const submitAdd = async () => {
    setSubmitting(true);
    try {
      await api.post('/wanted/add', { plate: chosenPlate, reason: chosenReason });
      toast.success(`Автомобиль ${chosenPlate} добавлен в розыск`);
      setAddStep(0);
      fetchVehicles();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка добавления');
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/wanted/${deleteTarget}`);
      toast.success(`Автомобиль ${deleteTarget} удалён из розыска`);
      setDeleteTarget(null);
      setSelectedPlate(null);
      fetchVehicles();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка удаления');
    }
  };

  if (loading) {
    return <div className="p-6 text-center">Загрузка...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-primary">Мой розыск</h1>
        <div className="flex gap-3">
          <button
            onClick={openAddDialog}
            className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-medium transition"
          >
            + Добавить в розыск
          </button>
          <button
            onClick={() => selectedPlate ? setDeleteTarget(selectedPlate) : toast.info('Сначала выберите строку в таблице')}
            className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium transition"
          >
            🗑 Удалить из розыска
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-primary text-white">
            <tr>
              <th className="p-3 text-left">ГРЗ</th>
              <th className="p-3 text-left">Модель</th>
              <th className="p-3 text-left">Цвет</th>
              <th className="p-3 text-left">Статус</th>
              <th className="p-3 text-left">Время</th>
              <th className="p-3 text-left">Дата</th>
              <th className="p-3 text-left">Адрес</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.length === 0 ? (
              <tr>
                <td colSpan="7" className="p-4 text-center text-gray-500">
                  Нет автомобилей в розыске
                </td>
              </tr>
            ) : (
              vehicles.map((v, i) => (
                <tr
                  key={i}
                  onClick={() => setSelectedPlate(v.plate)}
                  className={`border-b hover:bg-gray-50 cursor-pointer ${selectedPlate === v.plate ? 'bg-blue-50' : ''}`}
                >
                  <td className="p-3 font-bold">{v.plate}</td>
                  <td className="p-3">{v.model || '-'}</td>
                  <td className="p-3">{v.color || '-'}</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      v.status === 'В розыске' ? 'bg-red-500 text-white' :
                      v.status === 'Найден' ? 'bg-green-500 text-white' :
                      'bg-gray-500 text-white'
                    }`}>
                      {v.status}
                    </span>
                  </td>
                  <td className="p-3">{v.fix_time || '-'}</td>
                  <td className="p-3">{v.fix_date || '-'}</td>
                  <td className="p-3">{v.fix_address || '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Шаг 1: выбор ГРЗ */}
      {addStep === 1 && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-sm w-full p-6">
            <h3 className="text-lg font-bold text-primary mb-4">Добавление в розыск</h3>
            <label className="block text-sm text-gray-500 mb-1">ГРЗ</label>
            <select
              value={chosenPlate}
              onChange={(e) => setChosenPlate(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-6"
            >
              {availablePlates.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <div className="flex gap-3">
              <button onClick={goToReasonStep} className="flex-1 bg-success hover:bg-green-600 text-white font-bold py-2 rounded-lg">
                Далее
              </button>
              <button onClick={() => setAddStep(0)} className="flex-1 bg-gray-400 hover:bg-gray-500 text-white font-bold py-2 rounded-lg">
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Шаг 2: выбор причины розыска */}
      {addStep === 2 && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-sm w-full p-6">
            <h3 className="text-lg font-bold text-primary mb-2">Причина для {chosenPlate}</h3>
            <select
              value={chosenReason}
              onChange={(e) => setChosenReason(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-6 mt-4"
            >
            {violationCategories.map((cat, index) => (
                <option key={`category-${index}`} value={cat}>
                {cat}
                </option>
            ))}
            </select>
            <div className="flex gap-3">
              <button
                onClick={submitAdd}
                disabled={submitting}
                className="flex-1 bg-success hover:bg-green-600 text-white font-bold py-2 rounded-lg disabled:opacity-50"
              >
                {submitting ? 'Добавление...' : 'Добавить'}
              </button>
              <button onClick={() => setAddStep(1)} className="flex-1 bg-gray-400 hover:bg-gray-500 text-white font-bold py-2 rounded-lg">
                Назад
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Подтверждение удаления */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-sm w-full p-6 text-center">
            <p className="text-lg font-medium text-primary mb-6">
              Удалить {deleteTarget} из розыска?
            </p>
            <div className="flex gap-3">
              <button onClick={confirmDelete} className="flex-1 bg-danger hover:bg-red-600 text-white font-bold py-2 rounded-lg">
                Да
              </button>
              <button onClick={() => setDeleteTarget(null)} className="flex-1 bg-gray-400 hover:bg-gray-500 text-white font-bold py-2 rounded-lg">
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
