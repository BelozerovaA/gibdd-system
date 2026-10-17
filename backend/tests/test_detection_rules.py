"""Правила обработки события от сервиса камер (services/detection_rules.py).

Запуск из папки backend:   python -m unittest discover -s tests -v
Модуль правил не зависит от БД и FastAPI, поэтому тесты запускаются без них.
"""
import importlib.util
import os
import threading
import unittest
from datetime import datetime, timedelta, timezone

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PY = os.path.join(BACKEND_DIR, "app", "services", "detection_rules.py")

spec = importlib.util.spec_from_file_location("detection_rules_under_test", RULES_PY)
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)

NOW = datetime(2026, 10, 12, 12, 0, 0)


class PlateAndCameraTests(unittest.TestCase):
    def test_normalize_plate(self):
        self.assertEqual(rules.normalize_plate(" а123 вк43 "), "А123ВК43")
        self.assertEqual(rules.normalize_plate("А123ВК43"), "А123ВК43")

    def test_camera_number_from_code(self):
        self.assertEqual(rules.camera_number("CAM-08", 99), 8)
        self.assertEqual(rules.camera_number("CAM-15", 99), 15)

    def test_camera_number_fallback_when_no_digits(self):
        self.assertEqual(rules.camera_number("MAIN", 7), 7)
        self.assertEqual(rules.camera_number("", 7), 7)


class TimeTests(unittest.TestCase):
    def test_utc_is_converted_to_moscow_time(self):
        moment = datetime(2026, 10, 12, 9, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(rules.to_local_time(moment, "Europe/Moscow"), datetime(2026, 10, 12, 12, 0, 0))

    def test_offset_in_event_is_respected(self):
        moment = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone(timedelta(hours=3)))
        self.assertEqual(rules.to_local_time(moment, "Europe/Moscow"), datetime(2026, 10, 12, 12, 0, 0))

    def test_naive_time_is_treated_as_utc(self):
        self.assertEqual(rules.to_local_time(datetime(2026, 10, 12, 9, 0, 0), "Europe/Moscow"),
                         datetime(2026, 10, 12, 12, 0, 0))

    def test_unknown_timezone_falls_back_to_utc_plus_3(self):
        moment = datetime(2026, 10, 12, 9, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(rules.to_local_time(moment, "Нет/Такой"), datetime(2026, 10, 12, 12, 0, 0))

    def test_midnight_crossing_changes_date(self):
        moment = datetime(2026, 10, 12, 22, 30, 0, tzinfo=timezone.utc)
        self.assertEqual(rules.format_alert_moment(rules.to_local_time(moment, "Europe/Moscow")),
                         ("13.10.2026", "01:30:00"))

    def test_format_and_parse_roundtrip(self):
        date_str, time_str = rules.format_alert_moment(NOW)
        self.assertEqual((date_str, time_str), ("12.10.2026", "12:00:00"))
        self.assertEqual(rules.parse_alert_moment(date_str, time_str), NOW)

    def test_parse_of_broken_values_returns_none(self):
        self.assertIsNone(rules.parse_alert_moment("мусор", "12:00:00"))
        self.assertIsNone(rules.parse_alert_moment(None, None))


class DecideTests(unittest.TestCase):
    COOLDOWN = 120

    def alert(self, reaction, seconds_ago):
        return rules.LastAlert(reaction_status=reaction, created_at=NOW - timedelta(seconds=seconds_ago))

    def test_vehicle_not_wanted(self):
        self.assertEqual(rules.decide(False, None, NOW, self.COOLDOWN), rules.IGNORE_NOT_WANTED)

    def test_first_alert_is_created(self):
        self.assertIsNone(rules.decide(True, None, NOW, self.COOLDOWN))

    def test_unanswered_alert_blocks_new_one_even_if_old(self):
        last = self.alert(rules.REACTION_WAITING, seconds_ago=10_000)
        self.assertEqual(rules.decide(True, last, NOW, self.COOLDOWN), rules.IGNORE_PENDING)

    def test_recent_answered_alert_triggers_cooldown(self):
        self.assertEqual(rules.decide(True, self.alert("Принято", 119), NOW, self.COOLDOWN), rules.IGNORE_COOLDOWN)

    def test_cooldown_boundary_is_inclusive_of_the_limit(self):
        self.assertIsNone(rules.decide(True, self.alert("Принято", 120), NOW, self.COOLDOWN))
        self.assertIsNone(rules.decide(True, self.alert("Принято", 500), NOW, self.COOLDOWN))

    def test_event_older_than_last_alert_is_cooldown(self):
        last = rules.LastAlert("Принято", NOW + timedelta(seconds=30))
        self.assertEqual(rules.decide(True, last, NOW, self.COOLDOWN), rules.IGNORE_COOLDOWN)

    def test_zero_cooldown_disables_it(self):
        self.assertIsNone(rules.decide(True, self.alert("Принято", 0), NOW, 0))

    def test_unparsable_last_time_does_not_block(self):
        self.assertIsNone(rules.decide(True, rules.LastAlert("Принято", None), NOW, self.COOLDOWN))

    def test_not_wanted_wins_over_everything(self):
        self.assertEqual(rules.decide(False, self.alert(rules.REACTION_WAITING, 1), NOW, self.COOLDOWN),
                         rules.IGNORE_NOT_WANTED)


class EventDeduplicatorTests(unittest.TestCase):
    def test_remembers_added_events(self):
        d = rules.EventDeduplicator()
        self.assertFalse(d.contains("a"))
        d.add("a")
        self.assertTrue(d.contains("a"))

    def test_oldest_events_are_evicted(self):
        d = rules.EventDeduplicator(max_size=3)
        for i in range(5):
            d.add(f"e{i}")
        self.assertFalse(d.contains("e0"))
        self.assertFalse(d.contains("e1"))
        self.assertTrue(d.contains("e4"))

    def test_readding_refreshes_position(self):
        d = rules.EventDeduplicator(max_size=2)
        d.add("a"); d.add("b"); d.add("a"); d.add("c")
        self.assertTrue(d.contains("a"))
        self.assertFalse(d.contains("b"))

    def test_safe_for_parallel_use(self):
        d = rules.EventDeduplicator(max_size=50)
        def work(offset):
            for i in range(200):
                d.add(f"{offset}-{i}")
                d.contains(f"{offset}-{i}")
        threads = [threading.Thread(target=work, args=(n,)) for n in range(4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertLessEqual(len(d._seen), 50)


if __name__ == "__main__":
    unittest.main()
