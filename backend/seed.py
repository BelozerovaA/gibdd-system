import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app import models
from app.models import (
    Department, Employee, Vehicle, ViolationCategory,
    WantedVehicle, Camera,
)

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

department = db.query(Department).first()
if not department:
    department = Department(
        name="Управление ГИБДД по Кировской области",
        city="Киров",
        address="ул. Преображенская, 20",
        phone="+7 (8332) 11-22-33",
        chief_name="Смирнов Андрей Викторович",
    )
    db.add(department)
    db.commit()
    db.refresh(department)
    print(f" Подразделение создано: {department.name}")
EMPLOYEES = [
    ("belozerov_rv", "Admin2024", "Белозеров Роман Валерьевич", "Администратор", "belozerov@gibdd-kirov.example"),
    ("ivanov_ai", "Ivanov2024", "Иванов Алексей Игоревич", "Инспектор ДПС", "ivanov@gibdd-kirov.example"),
    ("petrova_ea", "Petrova2024", "Петрова Елена Андреевна", "Инспектор ДПС", "petrova@gibdd-kirov.example"),
    ("sidorov_mk", "Sidorov2024", "Сидоров Максим Константинович", "Старший инспектор", "sidorov@gibdd-kirov.example"),
    ("kuznetsova_ov", "Kuznec2024", "Кузнецова Ольга Викторовна", "Инспектор ДПС", "kuznetsova@gibdd-kirov.example"),
]

employees_by_login = {}
for login, password, full_name, position, email in EMPLOYEES:
    emp = db.query(Employee).filter(Employee.login == login).first()
    if not emp:
        emp = Employee(
            login=login,
            password=password,
            full_name=full_name,
            birth_date="14.03.1990",
            phone="+7 900 000-00-00",
            email=email,
            position=position,
            hire_date="01.09.2019",
            department_id=department.id,
            is_active=True,
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        print(f" Сотрудник создан: {full_name} (логин: {login} / пароль: {password})")
    employees_by_login[login] = emp

VIOLATIONS = [
    ("12.6", "Угон", "Угон транспортного средства", 120000),
    ("12.8", "Спецмероприятие", 'Оперативный план "Перехват"', 4000),
    ("12.1", "Нарушение ПДД", "Систематическое нарушение правил дорожного движения", 5000),
    ("12.27", "ДТП, скрылся с места", "Оставление места дорожно-транспортного происшествия", 30000),
    ("12.9", "Розыск свидетеля", "ТС разыскивается как участник происшествия", 0),
]
for code, name, desc, fine in VIOLATIONS:
    if not db.query(ViolationCategory).filter(ViolationCategory.code == code).first():
        db.add(ViolationCategory(code=code, name=name, description=desc, fine_amount=fine))
db.commit()

CAMERAS = [
    ("CAM-01", "ул. Дзержинского / ул. Луганская", 58.6142, 49.6350, "Стационарная", 60),
    ("CAM-02", "ул. Лепсе / Октябрьский пр-т", 58.5981, 49.6395, "Стационарная", 60),
    ("CAM-03", "ул. Лепсе / ул. Сормовская", 58.5940, 49.6280, "Стационарная", 60),
    ("CAM-04", "ул. Московская / ул. Производственная", 58.5882, 49.6520, "Стационарная", 60),
    ("CAM-05", "ул. Воровского / ул. Производственная", 58.5860, 49.6710, "Стационарная", 60),
    ("CAM-06", "ул. Воровского / пр-т Строителей", 58.5828, 49.6825, "Стационарная", 60),
    ("CAM-07", "ул. Щорса / ул. Производственная", 58.5895, 49.6602, "Стационарная", 60),
    ("CAM-08", "ул. Московская 106/1", 58.5990, 49.6547, "Мобильная", 60),
    ("CAM-09", "ул. Воровского / ул. Ивана Попова", 58.5795, 49.6910, "Стационарная", 60),
    ("CAM-10", "ул. Воровского / ул. Горького", 58.6033, 49.6673, "Стационарная", 40),
    ("CAM-11", "ул. Воровского / Октябрьский пр-т", 58.5975, 49.6650, "Стационарная", 60),
    ("CAM-12", "ул. Московская / Октябрьский пр-т", 58.6010, 49.6555, "Стационарная", 60),
    ("CAM-13", "ул. Преображенская / Октябрьский пр-т", 58.6035, 49.6600, "Стационарная", 40),
    ("CAM-14", "ул. Воровского / ул. Владимирская", 58.6068, 49.6748, "Стационарная", 40),
    ("CAM-15", "ул. Воровского / ул. Ленина", 58.6088, 49.6690, "Стационарная", 40),
]
for camera_id, address, lat, lon, cam_type, speed_limit in CAMERAS:
    if not db.query(Camera).filter(Camera.camera_id == camera_id).first():
        db.add(Camera(
            camera_id=camera_id, address=address, latitude=lat, longitude=lon,
            camera_type=cam_type, speed_limit=speed_limit, is_active=True,
        ))
db.commit()
print(f" Камеры: {db.query(Camera).count()} в базе")

MODELS = ["Lada Vesta", "Lada Granta", "Hyundai Solaris", "Kia Rio", "Toyota Camry",
          "Volkswagen Polo", "Renault Logan", "Skoda Octavia", "Nissan Almera",
          "Chevrolet Niva", "Ford Focus", "Mazda 3"]
COLORS = ["Белый", "Чёрный", "Серебристый", "Синий", "Красный", "Серый", "Зелёный"]
LETTERS = "АВЕКМНОРСТУХ"

def random_plate():
    return f"{random.choice(LETTERS)}{random.randint(100,999)}{random.choice(LETTERS)}{random.choice(LETTERS)}43"

existing_plates = {v.plate for v in db.query(Vehicle.plate).all()}
vehicles_created = []
target_count = 40
attempts = 0
while len(existing_plates) < target_count and attempts < 500:
    attempts += 1
    plate = random_plate()
    if plate in existing_plates:
        continue
    existing_plates.add(plate)
    v = Vehicle(
        plate=plate,
        model=random.choice(MODELS),
        color=random.choice(COLORS),
        vin=f"XW{random.randint(10**15, 10**16-1)}"[:17],
        owner_name="—",
        category="Легковой",
        is_stolen=False,
    )
    db.add(v)
    vehicles_created.append(v)
db.commit()
print(f" Автомобили: {db.query(Vehicle).count()} в базе")

if db.query(WantedVehicle).count() == 0:
    all_vehicles = db.query(Vehicle).all()
    all_categories = db.query(ViolationCategory).all()
    emp_list = list(employees_by_login.values())
    sample = random.sample(all_vehicles, min(10, len(all_vehicles)))
    for i, v in enumerate(sample):
        emp = emp_list[i % len(emp_list)]
        cat = random.choice(all_categories)
        wv = WantedVehicle(
            vehicle_id=v.id,
            employee_id=emp.id,
            violation_category_id=cat.id,
            reason=cat.name,
            wanted_date="01.09.2026",
            status="В розыске",
            is_active=True,
            reaction_status="Ожидает",
            found_status="Нет",
        )
        db.add(wv)
    db.commit()
    print(" Создано 10 автомобилей в розыске, распределённых между сотрудниками")

db.close()
print("\nГотово. Логины для входа (пароль указан рядом):")
for login, password, full_name, position, email in EMPLOYEES:
    print(f"  {login} / {password}  —  {full_name} ({position})")
