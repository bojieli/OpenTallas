"""WAVE-TICK-1119 (COORD 4, 5): CANCELLED rows archive out of the hot state under the state guard; unit_active asks systemctl once per listing"""
import json
import tempfile
import time
import unittest
from pathlib import Path
import autopilot as APM
from test_kit_wave import KW, cfg


class FakeAP:
    DRY = False

    def __init__(self):
        self.logs = []

    def log(self, x):
        self.logs.append(x)


def row(item, attempt, status, age_h, die="s81", event="e1"):
    return dict(die=die, event=event, item=item, attempt=attempt, status=status, updated=time.time() - age_h * 3600, **{"class": "SUPERSEDED"})


class Prune(unittest.TestCase):
    def state(self):
        return {"items": {
            "s81|a|b1": row("a", 1, "CANCELLED", 48),
            "s81|a|b2": row("a", 2, "CANCELLED", 47),          # newest attempt of a: kept
            "s81|b|b1": row("b", 1, "CANCELLED", 2),            # too young
            "s81|c|b1": row("c", 1, "FAIL", 100),               # not CANCELLED
            "s81|c|b2": row("c", 2, "CANCELLED", 100),          # newest of c: kept
            "cap|d|b1": row("d", 1, "CANCELLED", 100, die="cap"),
            "cap|d|b2": row("d", 2, "RUNNING", 1, die="cap"),
        }}

    def test_prunes_only_old_non_newest_cancelled(self):
        with tempfile.TemporaryDirectory() as t:
            c = cfg(); c["dies"]["cap"] = dict(max_items_total=5)
            st = self.state(); ap = FakeAP()
            self.assertEqual(KW.prune_terminal(ap, c, st, t), 1)
            self.assertNotIn("s81|a|b1", st["items"])
            self.assertEqual(len(st["items"]), 6)
            self.assertIn("s81|a|b1", st["pruned"])
            lines = (Path(t) / KW.ARCHIVE_FILE).read_text().splitlines()
            self.assertEqual([json.loads(x)["key"] for x in lines], ["s81|a|b1"])
            self.assertEqual(json.loads(lines[0])["row"]["attempt"], 1)
            self.assertEqual(KW.prune_terminal(ap, c, st, t), 0)       # idempotent

    def test_guard_accepts_the_prune_and_still_carries_unknown_losses(self):
        with tempfile.TemporaryDirectory() as t:
            c = cfg(); st = self.state(); ap = FakeAP()
            KW.save_state(json.loads(json.dumps(st)), t)               # disk has every row
            KW.prune_terminal(ap, c, st, t)
            KW.save_state(st, t)
            disk = json.loads((Path(t) / KW.STATE_FILE).read_text())
            self.assertNotIn("s81|a|b1", disk["items"])                # not carried back
            stale = {"items": {"s81|zzz|b1": row("zzz", 1, "RUNNING", 1)}}
            KW.save_state(stale, t)                                     # a stale writer with its own row: the pruned set survives, nothing is lost
            disk = json.loads((Path(t) / KW.STATE_FILE).read_text())
            self.assertIn("s81|zzz|b1", disk["items"])
            self.assertIn("s81|a|b1", disk["pruned"])
            self.assertNotIn("s81|a|b1", disk["items"])
            self.assertIn("cap|d|b2", disk["items"])                    # a row the prune did not name is still carried from disk

    def test_dry_run_prunes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            ap = FakeAP(); ap.DRY = True; st = self.state()
            self.assertEqual(KW.prune_terminal(ap, cfg(), st, t), 0)
            self.assertEqual(len(st["items"]), 7)


class UnitCache(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.old = APM.sh
        APM.UNIT_CACHE.update(t=0.0, set=None)

        def fake(cmd, timeout=300, input=None):
            self.calls.append(cmd)
            if "list-units" in cmd:
                return 0, "ap-a-a1.service loaded active running x\nap-b-a1.service loaded active running y\n", ""
            return (0, "inactive\n", "") if "is-active" in cmd else (1, "", "")
        APM.sh = fake

    def tearDown(self):
        APM.sh = self.old
        APM.UNIT_CACHE.update(t=0.0, set=None)

    def test_listed_units_cost_one_systemctl(self):
        for _ in range(100):
            self.assertTrue(APM.unit_active("ap-a-a1"))
            self.assertTrue(APM.unit_active("ap-b-a1.service"))
        self.assertEqual(len(self.calls), 1)

    def test_unlisted_unit_is_asked_individually(self):
        self.assertFalse(APM.unit_active("ap-new-a1"))
        self.assertEqual(sum("is-active" in c for c in self.calls), 1)

    def test_failed_listing_falls_back(self):
        APM.sh = lambda cmd, timeout=300, input=None: (1, "", "") if "list-units" in cmd else (0, "active\n", "")
        self.assertTrue(APM.unit_active("anything"))


if __name__ == "__main__":
    unittest.main()
