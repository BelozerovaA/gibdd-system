import React, { useState } from 'react';
import { useAlerts } from '../contexts/AlertContext';

const ALL_MAP = '/All_map.png';

export default function Map() {
  const { highlight, clearHighlight } = useAlerts();
  const [zoom, setZoom] = useState(1);

  const zoomIn = () => setZoom(prev => Math.min(prev + 0.2, 3));
  const zoomOut = () => setZoom(prev => Math.max(prev - 0.2, 0.5));
  const resetZoom = () => setZoom(1);

  // Если автомобиль только что зафиксирован, показываем карту с камерой № N
  // выделенной красным (public/cam_N.png), иначе общую карту.
  const mapSrc = highlight ? `/cam_${highlight.camera}.png` : ALL_MAP;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-primary">Карта камер видеофиксации</h1>
        <div className="flex gap-2 items-center">
          <button
            onClick={zoomOut}
            className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-medium transition"
          >
            − Уменьшить
          </button>
          <span className="text-sm font-medium text-gray-600 min-w-[80px] text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-medium transition"
          >
            + Увеличить
          </button>
          <button
            onClick={resetZoom}
            className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg font-medium transition"
          >
            Сброс
          </button>
        </div>
      </div>

      {highlight && (
        <div className="mb-4 flex items-center justify-between bg-red-50 border-l-4 border-danger rounded-r-lg px-4 py-3">
          <p className="text-sm text-gray-700">
            <span className="font-bold text-danger">Автомобиль {highlight.plate}</span>
            {' '}зафиксирован на камере №{highlight.camera}: {highlight.address}
          </p>
          <button
            onClick={clearHighlight}
            className="ml-4 shrink-0 bg-gray-500 hover:bg-gray-600 text-white px-3 py-1 rounded-lg text-sm font-medium transition"
          >
            Снять подсветку
          </button>
        </div>
      )}

      {/* Карта с зумом */}
      <div className="bg-white rounded-xl shadow-md overflow-auto" style={{ height: '700px' }}>
        <div
          className="transition-transform duration-300 origin-top-left"
          style={{
            transform: `scale(${zoom})`,
            width: '100%',
          }}
        >
          <img
            src={mapSrc}
            alt={highlight ? `Карта, камера №${highlight.camera}` : 'Карта камер'}
            // если нужной картинки нет, показываем общую карту
            onError={(e) => {
              if (!e.currentTarget.src.endsWith(ALL_MAP)) e.currentTarget.src = ALL_MAP;
            }}
            className="w-full h-auto select-none"
            draggable={false}
          />
        </div>
      </div>
    </div>
  );
}
