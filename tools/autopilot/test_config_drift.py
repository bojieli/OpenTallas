"""FLOW-HEALTH-1 11-15 item 5: kit_wave.json drift ALERT (working copy vs origin/coord/state for more than one tick)"""
import tempfile
import unittest
from pathlib import Path
import kit_wave as KW


class AP:
    def __init__(self, d):
        self.COORD, self.logs, self.q = Path(d), [], []

    def log(self, m):
        self.logs.append(m)

    def coord_append(self, rel, line):
        self.q.append(line)


class Drift(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        (Path(self.d) / "autopilot").mkdir()
        self.f = Path(self.d) / "autopilot/kit_wave.json"
        self.ap = AP(self.d)
        self.st = {}

    def tick(self, origin, now):
        return KW.config_drift(self.ap, self.st, now=now, read_origin=lambda: origin)

    def test_same_is_quiet(self):
        self.f.write_bytes(b"{}")
        self.assertIsNone(self.tick(b"{}", 1))
        self.assertEqual(self.ap.q, [])

    def test_alert_after_more_than_one_tick_once(self):
        self.f.write_bytes(b'{"a":1}')
        self.tick(b"{}", 100)
        self.assertEqual(self.ap.q, [])                       # one tick: an edit about to be committed
        self.tick(b"{}", 160)
        self.assertEqual(len(self.ap.q), 1)
        self.assertIn("ALERT", self.ap.q[0])
        self.tick(b"{}", 220)
        self.assertEqual(len(self.ap.q), 1)                   # once

    def test_new_content_restarts_and_match_resolves(self):
        self.f.write_bytes(b'{"a":1}')
        self.tick(b"{}", 1); self.tick(b"{}", 2)
        self.f.write_bytes(b'{"a":2}')
        self.tick(b"{}", 3)
        self.assertEqual(len(self.ap.q), 1)                   # restart: 1 tick of the new content
        self.tick(b"{}", 4)
        self.assertEqual(len(self.ap.q), 2)
        self.tick(b'{"a":2}', 5)
        self.assertIn("RESOLVED", self.ap.q[-1])
        self.assertEqual(self.st["flow_guard"]["drift"], {})

    def test_no_origin_ref_is_unknown(self):
        self.f.write_bytes(b"{}")
        self.assertIsNone(self.tick(None, 1))
        self.assertEqual(self.ap.q, [])


if __name__ == "__main__":
    unittest.main()
