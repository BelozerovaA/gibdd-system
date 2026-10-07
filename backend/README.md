"""Выбор SMTP-сервера в EmailNotifier (без сети и без остальных модулей приложения).

Запуск из папки backend:   python -m unittest discover -s tests -v
"""
import importlib.util
import os
import unittest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL_PY = os.path.join(BACKEND_DIR, "app", "services", "email.py")
KEYS = ("SMTP_USER", "SMTP_PASSWORD", "SMTP_SERVER", "SMTP_PORT")


def make_notifier(**env):
    """Создаёт EmailNotifier с заданными переменными окружения."""
    saved = {k: os.environ.get(k) for k in KEYS}
    try:
        for k in KEYS:
            os.environ.pop(k, None)
        os.environ.update(env)
        spec = importlib.util.spec_from_file_location("email_service_under_test", EMAIL_PY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.EmailNotifier()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class EmailServerSelectionTests(unittest.TestCase):
    def test_gmail_by_domain(self):
        n = make_notifier(SMTP_USER="a@gmail.com")
        self.assertEqual((n.smtp_server, n.smtp_port), ("smtp.gmail.com", 587))

    def test_yandex_by_domain(self):
        for user in ("a@yandex.ru", "a@ya.ru"):
            n = make_notifier(SMTP_USER=user)
            self.assertEqual((n.smtp_server, n.smtp_port), ("smtp.yandex.ru", 465))

    def test_unknown_domain_falls_back_to_yandex(self):
        n = make_notifier(SMTP_USER="a@example.test")
        self.assertEqual((n.smtp_server, n.smtp_port), ("smtp.yandex.ru", 465))

    def test_explicit_server_and_port_win_over_domain(self):
        n = make_notifier(SMTP_USER="a@gmail.com", SMTP_SERVER="smtp.mail.ru", SMTP_PORT="465")
        self.assertEqual((n.smtp_server, n.smtp_port), ("smtp.mail.ru", 465))

    def test_invalid_port_is_ignored(self):
        n = make_notifier(SMTP_USER="a@gmail.com", SMTP_SERVER="smtp.mail.ru", SMTP_PORT="abc")
        self.assertEqual((n.smtp_server, n.smtp_port), ("smtp.gmail.com", 587))

    def test_server_without_port_is_ignored(self):
        n = make_notifier(SMTP_USER="a@gmail.com", SMTP_SERVER="smtp.mail.ru")
        self.assertEqual((n.smtp_server, n.smtp_port), ("smtp.gmail.com", 587))


if __name__ == "__main__":
    unittest.main()
