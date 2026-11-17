import json, os, tempfile, unittest
from pathlib import Path
import apply_reviewed_tree_marker as A
import hold_records as HR

SHA = "13f758a4fe342e4838cebd2401f11f37570e92e46e226642e518ad78245f776d"


class TC:
    @staticmethod
    def identity(die, tree, want, hosts, checker): return dict(die=die, tree=tree)
    @staticmethod
    def read(d, ident): return dict(state="ok", full_ok=True, running=False, main_sha="a" * 40)
    @staticmethod
    def location(d, ident): return Path(d) / "x"


def mk(die_extra=None):
    c = Path(tempfile.mkdtemp()); (c / "autopilot").mkdir(); (c / "lanes/handoff").mkdir(parents=True)
    d = {"src": "/x/old", "event": "E0", "plan": "/p0", "plan_sha256": "s0", "hold_event_items": {"s0": ["t3", "t1"]}}
    d.update(die_extra or {})
    (c / "autopilot/kit_wave.json").write_text(json.dumps({"dies": {"kv": d}}))
    return c


def cand():
    return {"die": "kv", "tree": "/x/new", "manifest_hash": SHA, "smoke": "PASS", "plan": "/p1", "plan_sha256": "s1", "hosts": ["epyc10"]}


class Apply(unittest.TestCase):
    def test_atomic_apply_adds_the_pilot_hold_and_queues_the_old_tree(self):
        c = mk()
        r = A.apply_marker(c, cand(), "/x/old", "E0", pilot_item="t1", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["src"], "/x/new"); self.assertEqual(d["superseded_trees"], ["/x/old"])
        rec = [x for x in d["hold_records"] if x.get("auto_pilot")][0]
        self.assertEqual(rec["release"], ["gen_pilot:kv:13f758a4fe34"]); self.assertEqual(rec["pilot_items"], ["t1"])
        self.assertEqual(r["pilot"]["item"], "t1"); self.assertTrue(r["pilot"]["hold_added"])
        self.assertTrue((c / "lanes/handoff/tree_switch_kv.json").exists())

    def test_default_pilot_item_is_the_smallest_known_item(self):
        c = mk()
        A.apply_marker(c, cand(), "/x/old", "E0", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["pilot_item"], "t1")

    def test_no_resolvable_pilot_refuses_before_writing(self):
        c = mk({"hold_event_items": {}})
        with self.assertRaises(SystemExit):
            A.apply_marker(c, cand(), "/x/old", "E0", TC=TC)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["src"], "/x/old")                         # untouched
        r = A.apply_marker(c, cand(), "/x/old", "E0", no_pilot=True, TC=TC)
        self.assertEqual(r["pilot"], "NONE")

    def test_stale_expectation_refused(self):
        c = mk()
        with self.assertRaises(AssertionError):
            A.apply_marker(c, cand(), "/x/other", "E0", pilot_item="t1", TC=TC)
