import React from 'react';
import { useAlerts } from '../contexts/AlertContext';

export default function DetectionModal() {
  const { detection, askFound, acceptDetection, answerFound } = useAlerts();

  if (detection) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden animate-pulse-once">
          <div className="bg-danger text-white px-6 py-4">
            <h2 className="text-lg font-bold"> ВНИМАНИЕ! Обнаружен автомобиль</h2>
          </div>
          <div className="p-6 space-y-2">
            <p><span className="text-gray-500">Гос. номер:</span> <span className="font-bold text-xl">{detection.plate}</span></p>
            <p><span className="text-gray-500">Место:</span> {detection.address}</p>
            <p><span className="text-gray-500">Дата/время:</span> {detection.date} {detection.time}</p>
          </div>
          <div className="px-6 pb-6">
            <button
              onClick={acceptDetection}
              className="w-full bg-success hover:bg-green-600 text-white font-bold py-3 rounded-lg transition"
            >
              Принято
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (askFound) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-2xl max-w-sm w-full overflow-hidden">
          <div className="p-6 text-center">
            <p className="text-lg font-bold text-primary mb-6">
              Автомобиль {askFound.plate} задержан?
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => answerFound(true)}
                className="flex-1 bg-success hover:bg-green-600 text-white font-bold py-2 rounded-lg transition"
              >
                Да
              </button>
              <button
                onClick={() => answerFound(false)}
                className="flex-1 bg-danger hover:bg-red-600 text-white font-bold py-2 rounded-lg transition"
              >
                Нет
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
