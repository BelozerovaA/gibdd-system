"""Проверка загрузчика тестовых сотрудников (seed_data.py).

Запуск из папки backend:   python -m unittest discover -s tests -v
Тесты не требуют БД и сторонних библиотек.
"""
import json
import os
import sys
import tempfile
import unittest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from seed_data import SeedConfigError, load_employees, resolve_path  # noqa: E402

EXAMPLE = os.path.join(BACKEND_DIR, "seed_users.example.json")


def write_json(directory, name, data):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def employee(**overrides):
    base = {
        "login": "user1", "password": "Pass1", "full_name": "Тестов Тест Тестович",
        "position": "Инспектор ДПС", "email": "t@example.test",
    }
    base.update(overrides)
    return base


class SeedDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ.pop("SEED_USERS_FILE", None)

    def test_example_template_is_valid(self):
        employees = load_employees(BACKEND_DIR, EXAMPLE)
        self.assertGreaterEqual(len(employees), 1)
        self.assertEqual(len({e["login"] for e in employees}), len(employees))

    def test_default_file_name_is_seed_users_json(self):
        self.assertTrue(resolve_path(BACKEND_DIR).endswith("seed_users.json"))

    def test_missing_file_gives_hint_how_to_create_it(self):
        with self.assertRaises(SeedConfigError) as ctx:
            load_employees(self.tmp.name)
        self.assertIn("seed_users.example.json", str(ctx.exception))

    def test_path_from_environment_variable(self):
        path = write_json(self.tmp.name, "custom.json", {"employees": [employee()]})
        os.environ["SEED_USERS_FILE"] = path
        try:
            self.assertEqual(load_employees(BACKEND_DIR)[0]["login"], "user1")
        finally:
            os.environ.pop("SEED_USERS_FILE", None)

    def test_relative_path_is_resolved_from_base_dir(self):
        write_json(self.tmp.name, "users.json", {"employees": [employee()]})
        self.assertEqual(load_employees(self.tmp.name, "users.json")[0]["login"], "user1")

    def test_broken_json(self):
        path = os.path.join(self.tmp.name, "bad.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{не json")
        with self.assertRaises(SeedConfigError):
            load_employees(self.tmp.name, path)

    def test_missing_employees_key_or_empty_list(self):
        for data in ({}, {"employees": []}, [], {"employees": "x"}):
            path = write_json(self.tmp.name, "x.json", data)
            with self.assertRaises(SeedConfigError, msg=str(data)):
                load_employees(self.tmp.name, path)

    def test_required_fields_are_checked(self):
        for field in ("login", "password", "full_name", "position", "email"):
            bad = employee()
            del bad[field]
            path = write_json(self.tmp.name, "x.json", {"employees": [bad]})
            with self.assertRaises(SeedConfigError, msg=field) as ctx:
                load_employees(self.tmp.name, path)
            self.assertIn(field, str(ctx.exception))

    def test_blank_password_rejected(self):
        path = write_json(self.tmp.name, "x.json", {"employees": [employee(password="   ")]})
        with self.assertRaises(SeedConfigError):
            load_employees(self.tmp.name, path)

    def test_duplicate_logins_rejected(self):
        path = write_json(self.tmp.name, "x.json", {"employees": [employee(), employee()]})
        with self.assertRaises(SeedConfigError) as ctx:
            load_employees(self.tmp.name, path)
        self.assertIn("повторяется", str(ctx.exception))


class SeedHasNoSecretsTests(unittest.TestCase):
    def test_seed_py_contains_no_passwords(self):
        with open(os.path.join(BACKEND_DIR, "seed.py"), encoding="utf-8") as f:
            source = f.read()
        with open(EXAMPLE, encoding="utf-8") as f:
            passwords = [e["password"] for e in json.load(f)["employees"]]
        for password in passwords:
            self.assertNotIn(password, source)


if __name__ == "__main__":
    unittest.main()
