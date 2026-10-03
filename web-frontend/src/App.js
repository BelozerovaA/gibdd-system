import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './index.css';

import { store } from './store';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import MyWanted from './pages/MyWanted';
import AllWanted from './pages/AllWanted';
import AlertsHistory from './pages/AlertsHistory';
import Map from './pages/Map';
import Profile from './pages/Profile';
import PrivateRoute from './components/PrivateRoute';
import Layout from './components/Layout';

function App() {
  return (
    <Provider store={store}>
      <Router>
        <ToastContainer position="bottom-right" autoClose={4000} />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index element={<Navigate to="/dashboard" />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="my-wanted" element={<MyWanted />} />
            <Route path="all-wanted" element={<AllWanted />} />
            <Route path="history" element={<AlertsHistory />} />
            <Route path="map" element={<Map />} />
            <Route path="profile" element={<Profile />} />
          </Route>
        </Routes>
      </Router>
    </Provider>
  );
}

export default App;