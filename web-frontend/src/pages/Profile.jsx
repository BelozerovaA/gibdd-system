import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import api from '../services/api';
import { toast } from 'react-toastify';

export default function Profile() {
  const { user } = useSelector((state) => state.auth);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get('/employees/me')
      .then((res) => {
        setProfile(res.data);
        setEmail(res.data.email || '');
        setPhone(res.data.phone || '');
      })
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await api.put('/employees/me', {
        email: email.trim() || null,
        phone: phone.trim() || null,
      });
      setProfile(data);
      toast.success('Профиль сохранён');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось сохранить');
    } finally {
      setSaving(false);
    }
  };

  const data = profile || {};

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-primary mb-6">Личный кабинет</h1>

      <div className="bg-white rounded-xl shadow-md p-6 max-w-2xl">
        {loading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : (
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="text-sm text-gray-500">ФИО</label>
              <p className="text-lg font-medium">{data.full_name || user?.full_name}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">Должность</label>
              <p className="text-lg font-medium">{data.position || user?.position}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500 block mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="email@example.com"
              />
              <p className="text-xs text-gray-400 mt-1">На этот адрес приходят оповещения о розыске</p>
            </div>
            <div>
              <label className="text-sm text-gray-500 block mb-1">Телефон</label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="+7 ..."
              />
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
            <button
              type="submit"
              disabled={saving}
              className="mt-2 px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium transition"
            >
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
