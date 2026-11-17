"""FABLE-FLOW-2200: releasing a hold that covers more than 3 items launches ONE pilot first; the rest stay held until it passes GEN."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR  # noqa: E402
import kit_wave as KW  # noqa: E402

PLAN = "p" * 64
ITEMS = [f"t{i:02d}" for i in range(34)]


def cfg(items=ITEMS, store=True, **extra):
    c = {"dies": {"s81": {"event": "B6gG3", "plan": "/x/B6gG3.json", "plan_sha256": PLAN, "hold_event_items": {PLAN: list(items)}}}}
    if store:
        c["_release_pilot"] = {}
    c.update(extra)
    HR.add_record(c, "s81", {"id": "svc", "plan_sha": PLAN, "reason": "tree fix", "release": ["event_adopt:B6gG3"], "patterns": ["t*"]})
    return c


def compile_(c, rows=()):
    c["_item_rows"] = list(rows)
    c["_item_active"] = {}
    for r in rows:
        if r.get("status") in ("RUNNING", "ENQUEUED", "PASS", "ROUTE-HELD", "SIGNED"):
            c["_item_active"].setdefault(r["die"], []).append(r["item"])
    return HR.compile_holds(c, KW.hold_ctx(c))


class ReleasePilot(unittest.TestCase):
    def test_bulk_release_launches_one_pilot(self):
        c = cfg()
        c["_now"] = 1000.0
        rel = compile_(c)
        self.assertEqual(len(rel), 1)                                          # ONE released
        pilot = rel[0][1]
        held = c["dies"]["s81"]["hold_items"]
        self.assertEqual(len(held), 33)
        self.assertNotIn(pilot, held)
        self.assertTrue(all("RELEASE PILOT" in v and pilot in v for v in held.values()))
        self.assertEqual(c["_release_pilot"]["s81|svc"]["pilot"], pilot)

    def test_pilot_is_the_die_choice_then_the_smallest_item(self):
        c = cfg()
        c["dies"]["s81"]["pilot_item"] = "t17"
        self.assertEqual(compile_(c)[0][1], "t17")
        c = cfg()
        c["_item_cells"] = {("s81", i): 5000 - n for n, i in enumerate(ITEMS)}   # t33 is the smallest
        self.assertEqual(compile_(c)[0][1], "t33")

    def test_rest_stay_held_while_the_pilot_runs_or_fails(self):
        c = cfg()
        c["_now"] = 1000.0
        pilot = compile_(c)[0][1]
        for status in ("RUNNING", "FAIL"):
            c2 = cfg()
            c2["_release_pilot"] = c["_release_pilot"]
            rel = compile_(c2, [{"die": "s81", "item": pilot, "status": status, "started": 1001}])
            self.assertEqual([k for _, k, _ in rel], [pilot], status)
            self.assertEqual(len(c2["dies"]["s81"]["hold_items"]), 33, status)

    def test_a_pilot_that_passes_gen_releases_the_rest(self):
        c = cfg()
        c["_now"] = 1000.0
        pilot = compile_(c)[0][1]
        c2 = cfg()
        c2["_release_pilot"] = c["_release_pilot"]
        rel = compile_(c2, [{"die": "s81", "item": pilot, "status": "PASS", "started": 1500}])
        self.assertEqual(len(rel), 34)
        self.assertEqual(c2["dies"]["s81"]["hold_items"], {})
        self.assertTrue(c2["_release_pilot"]["s81|svc"]["passed"])
        c3 = cfg()                                                              # and stays released after the pilot row ages out
        c3["_release_pilot"] = c2["_release_pilot"]
        self.assertEqual(len(compile_(c3)), 34)

    def test_an_old_pass_before_the_release_is_no_pilot_pass(self):
        c = cfg()
        c["_now"] = 5000.0
        pilot = compile_(c)[0][1]
        c2 = cfg()
        c2["_release_pilot"] = c["_release_pilot"]
        rel = compile_(c2, [{"die": "s81", "item": pilot, "status": "PASS", "started": 100}])
        self.assertEqual(len(rel), 1)

    def test_small_releases_and_already_launched_releases_are_untouched(self):
        c = cfg(items=ITEMS[:3])
        self.assertEqual(len(compile_(c)), 3)                                   # 3 items: all at once
        self.assertEqual(c["_release_pilot"], {})
        c = cfg()
        rel = compile_(c, [{"die": "s81", "item": "t05", "status": "RUNNING", "started": 1}])
        self.assertEqual(len(rel), 34)                                          # already launched before the gate existed: no re-hold
        self.assertTrue(c["_release_pilot"]["s81|svc"]["passed"])
        c = cfg()
        rel = compile_(c, [{"die": "s81", "item": "t05", "status": "FAIL", "started": 1}])
        self.assertEqual(len(rel), 1)                                           # an old FAIL row is not a launch

    def test_fails_open(self):
        self.assertEqual(len(compile_(cfg(store=False))), 34)                   # no state store: old behaviour
        c = cfg()
        c["dies"]["s81"]["hold_records"][0]["pilot_release"] = False             # a record may opt out
        self.assertEqual(len(compile_(c)), 34)

    def test_kit_wave_wires_state_and_the_pass_test(self):
        src = (Path(__file__).resolve().parent / "kit_wave.py").read_text()
        self.assertIn('st.setdefault("hold_release_pilot", {})', src)
        self.assertIn("release_pilot_fn=lambda die, item, t0: release_pilot_passed(", src)
        self.assertTrue(KW.release_pilot_passed([{"die": "d", "item": "i", "status": "SIGNED", "started": 10}], "d", "i", 5))
        self.assertFalse(KW.release_pilot_passed([{"die": "d", "item": "i", "status": "FAIL", "started": 10}], "d", "i", 5))


if __name__ == "__main__":
    unittest.main()
