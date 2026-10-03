import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { logout } from '../store';
import { AlertProvider } from '../contexts/AlertContext';
import DetectionModal from './DetectionModal';
import api from '../services/api';
import {
  HomeIcon,
  MagnifyingGlassIcon,
  ListBulletIcon,
  MapIcon,
  ClockIcon,
  UserIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';

export default function Layout() {
  const { user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const handleLogout = () => {
    api.post('/simulator/stop').catch(() => {});
    dispatch(logout());
    navigate('/login');
  };

  const navItems = [
    { path: '/dashboard', label: 'Главная', icon: HomeIcon },
    { path: '/my-wanted', label: 'Мой розыск', icon: MagnifyingGlassIcon },
    { path: '/all-wanted', label: 'База розыска', icon: ListBulletIcon },
    { path: '/map', label: 'Карта', icon: MapIcon },
    { path: '/history', label: 'История', icon: ClockIcon },
    { path: '/profile', label: 'Профиль', icon: UserIcon },
  ];

  return (
    <AlertProvider>
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-primary text-white flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-xl font-bold">ГИБДД КИРОВ</h1>
          <p className="text-xs text-gray-400">Система розыска</p>
        </div>

        <nav className="flex-1 p-2">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center px-4 py-3 rounded-lg transition ${
                  isActive
                    ? 'bg-secondary text-white'
                    : 'hover:bg-gray-700 text-gray-300'
                }`
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              <span className="text-sm font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium truncate">{user?.full_name}</p>
              <p className="text-xs text-gray-400 truncate">{user?.position}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-gray-700 rounded-lg transition"
            >
              <ArrowRightOnRectangleIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
    <DetectionModal />
    </AlertProvider>
  );
}