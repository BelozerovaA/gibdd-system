import os
import random
import time
from threading import Thread
from datetime import datetime

from ..database import SessionLocal
from ..models import WantedVehicle, Vehicle, Camera, Alert

# Как часто (в секундах) симулятор пытается "обнаружить" автомобиль.
# Для демонстрации можно уменьшить через DETECTION_INTERVAL_SECONDS в backend/.env
DETECTION_INTERVAL_SECONDS = int(os.getenv("DETECTION_INTERVAL_SECONDS", "60"))


def _camera_number(cam) -> int:
    """Номер камеры на карте: «CAM-08» -> 8 (по нему выбирается картинка cam_8.png)."""
    digits = "".join(ch for ch in (cam.camera_id or "") if ch.isdigit())
    return int(digits) if digits else cam.id


class TrafficSimulator:
    """Симулятор фиксации разыскиваемых автомобилей камерами."""

    def __init__(self, employee_id: int, interval: int = DETECTION_INTERVAL_SECONDS):
        self.employee_id = employee_id
        self.interval = interval
        self.running = False
        self.thread = None
        self.on_detected_callback = None
        self.paused = False  # ставится в True, пока ждём реакции пользователя на предыдущее обнаружение

    def start(self, callback=None):
        if self.running:
            return
        self.running = True
        self.on_detected_callback = callback
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def is_running(self):
        return self.running

    def _run(self):
        while self.running:
            for _ in range(self.interval):
                if not self.running:
                    return
                time.sleep(1)
            if self.paused:
                continue
            try:
                self._process_detection()
            except Exception as e:
                print(f"❌ Ошибка в симуляторе (employee={self.employee_id}): {e}")

    def _process_detection(self):
        db = SessionLocal()
        try:
            candidates = (
                db.query(WantedVehicle)
                .join(Vehicle)
                .filter(
                    WantedVehicle.employee_id == self.employee_id,
                    WantedVehicle.is_active == True,
                    (WantedVehicle.found_status == "Нет") | (WantedVehicle.found_status.is_(None)),
                )
                .all()
            )
            if not candidates:
                return

            cameras = db.query(Camera).filter(Camera.is_active == True).all()
            if not cameras:
                return

            target = random.choice(candidates)
            cam = random.choice(cameras)
            dt = datetime.now()
            date_str = dt.strftime("%d.%m.%Y")
            time_str = dt.strftime("%H:%M:%S")

            target.fix_date = date_str
            target.fix_time = time_str
            target.fix_address = cam.address
            target.fix_camera_id = str(cam.id)
            target.reaction_status = "Ожидает"

            alert = Alert(
                wanted_id=target.id,
                camera_id=cam.id,
                vehicle_plate=target.vehicle.plate,
                alert_date=date_str,
                alert_time=time_str,
                address=cam.address,
                employee_id=self.employee_id,
                reaction_status="Ожидает",
                found_status="Нет",
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)

            payload = {
                "alert_id": alert.id,
                "wanted_id": target.id,
                "plate": target.vehicle.plate,
                "camera_id": cam.id,
                "camera_number": _camera_number(cam),
                "address": cam.address,
                "latitude": cam.latitude,
                "longitude": cam.longitude,
                "date": date_str,
                "time": time_str,
            }

            if self.on_detected_callback:
                self.pause()
                self.on_detected_callback(payload)

            print(f"🚨 Обнаружен автомобиль {target.vehicle.plate} на камере {cam.id} ({cam.address})")
        finally:
            db.close()


class SimulatorManager:
    """Держит по одному симулятору на каждого залогиненного сотрудника."""

    def __init__(self):
        self._simulators = {}

    def start(self, employee_id: int, callback):
        sim = self._simulators.get(employee_id)
        if sim and sim.is_running():
            # Пользователь заново открыл приложение (например, обновил страницу):
            # предыдущее окно оповещения потеряно, значит ждать реакции на него
            # больше нельзя, иначе симулятор остался бы на паузе навсегда.
            sim.resume()
            return sim
        sim = TrafficSimulator(employee_id)
        self._simulators[employee_id] = sim
        sim.start(callback)
        return sim

    def stop(self, employee_id: int):
        sim = self._simulators.pop(employee_id, None)
        if sim:
            sim.stop()

    def resume_after_reaction(self, employee_id: int):
        sim = self._simulators.get(employee_id)
        if sim:
            sim.resume()

    def status(self, employee_id: int) -> bool:
        sim = self._simulators.get(employee_id)
        return bool(sim and sim.is_running())


simulator_manager = SimulatorManager()
