import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import api from '../services/api';

export default function Profile() {
  const { user } = useSelector((state) => state.auth);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/employees/me')
      .then((res) => setProfile(res.data))
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, []);

  const data = profile || {};

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-primary mb-6">Личный кабинет</h1>

      <div className="bg-white rounded-xl shadow-md p-6 max-w-2xl">
        {loading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="text-sm text-gray-500">ФИО</label>
              <p className="text-lg font-medium">{data.full_name || user?.full_name}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">Должность</label>
              <p className="text-lg font-medium">{data.position || user?.position}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">Email</label>
              <p className="text-lg font-medium">{data.email || user?.email || 'Не указан'}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">Телефон</label>
              <p className="text-lg font-medium">{data.phone || 'Не указан'}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">Дата рождения</label>
              <p className="text-lg font-medium">{data.birth_date || '-'}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">Дата приёма на службу</label>
              <p className="text-lg font-medium">{data.hire_date || '-'}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">Подразделение</label>
              <p className="text-lg font-medium">{data.department_name || 'Не указано'}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
