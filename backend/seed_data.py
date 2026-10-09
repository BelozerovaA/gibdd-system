import json
import os
from typing import Dict, List, Optional

DEFAULT_FILE = "seed_users.json"
REQUIRED_FIELDS = ("login", "password", "full_name", "position", "email")


class SeedConfigError(Exception):
    """Файл с тестовыми сотрудниками отсутствует или заполнен неверно."""

def resolve_path(base_dir: str, path: Optional[str] = None) -> str:
    chosen = path or os.getenv("SEED_USERS_FILE") or DEFAULT_FILE
    return chosen if os.path.isabs(chosen) else os.path.join(base_dir, chosen)


def load_employees(base_dir: str, path: Optional[str] = None) -> List[Dict[str, str]]:
    full_path = resolve_path(base_dir, path)

    if not os.path.exists(full_path):
        raise SeedConfigError(
            f"Не найден файл с тестовыми сотрудниками: {full_path}\n"
            f"Создайте его из шаблона:  copy seed_users.example.json seed_users.json  "
            f"(Linux/Mac: cp seed_users.example.json seed_users.json)\n"
            f"Другой путь можно задать переменной SEED_USERS_FILE в .env"
        )

    try:
        with open(full_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise SeedConfigError(f"Файл {full_path} не является корректным JSON: {e}")

    employees = data.get("employees") if isinstance(data, dict) else None
    if not isinstance(employees, list) or not employees:
        raise SeedConfigError(
            f'В файле {full_path} должен быть ключ "employees" со списком сотрудников'
        )

    seen = set()
    for index, item in enumerate(employees, start=1):
        if not isinstance(item, dict):
            raise SeedConfigError(f"Сотрудник №{index} в {full_path} должен быть объектом")
        for field in REQUIRED_FIELDS:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise SeedConfigError(
                    f'У сотрудника №{index} в {full_path} не заполнено поле "{field}"'
                )
        if item["login"] in seen:
            raise SeedConfigError(f'Логин "{item["login"]}" повторяется в {full_path}')
        seen.add(item["login"])

    return employees
