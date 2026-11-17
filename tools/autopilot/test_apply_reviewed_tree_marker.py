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

    def test_superseded_auto_pilot_is_preserved_in_apply_receipt(self):
        old = {"id": "pilot-kv-deadbeefdead", "plan_sha": "s0", "items": ["*"],
               "pilot_items": ["t3"], "release": ["gen_pilot:kv:deadbeefdead"],
               "reason": "old source", "auto_pilot": True, "follow_plan": True}
        physical = {"id": "physical", "plan_sha": "s0", "items": ["t3"],
                    "release": ["proof:cts"], "reason": "physical proof", "carry": True}
        c = mk({"hold_records": [old, physical]})
        result = A.apply_marker(c, cand(), "/x/old", "E0", pilot_item="t1", TC=TC)
        after = json.loads((c / "autopilot/kit_wave.json").read_text())
        records = after["dies"]["kv"]["hold_records"]
        self.assertIn(physical, records)
        self.assertNotIn(old, records)
        receipt = json.loads(Path(result["receipt"]).read_text())
        self.assertEqual(receipt["pilot"]["retired"], [old])
        self.assertNotIn("retired_pilots", after)
        self.assertNotIn("retired_pilots", after["dies"]["kv"])

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


class KeepGenHosts(unittest.TestCase):
    """HEAD-DIE-R (COORD r400/r401): keep_gen_hosts keeps the die's current gen_hosts, guarded and fail-closed."""

    def _tc(self, seen, mutate=None):
        class T(TC):
            @staticmethod
            def identity(die, tree, want, hosts, checker):
                seen.append(sorted(hosts)); return dict(die=die, tree=tree, hosts=sorted(hosts))
            @staticmethod
            def read(d, ident):
                if mutate:
                    mutate()
                return dict(state="ok", full_ok=True, running=False, main_sha="a" * 40)
        return T

    def test_keeps_current_hosts_and_guards_them(self):
        c = mk({"gen_hosts": ["epyc10", "epyc8"], "gen_host": "epyc8"})
        seen = []
        o = dict(cand(), config={"gen_hosts": ["epyc10"], "gen_host": "epyc10"})
        A.apply_marker(c, {"marker": o, "keep_gen_hosts": True}, "/x/old", "E0", pilot_item="t1", TC=self._tc(seen))
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["gen_hosts"], ["epyc10", "epyc8"]); self.assertEqual(d["gen_host"], "epyc8")
        self.assertEqual(seen, [["epyc10", "epyc8"]])

    def test_flag_argument_equals_candidate_key(self):
        c = mk({"gen_hosts": ["epyc10", "epyc8"]})
        A.apply_marker(c, cand(), "/x/old", "E0", pilot_item="t1", TC=self._tc([]), keep_gen_hosts=True)
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["gen_hosts"], ["epyc10", "epyc8"]); self.assertEqual(d["gen_host"], "epyc10")

    def test_hosts_changed_after_guard_read_refuses_untouched(self):
        c = mk({"gen_hosts": ["epyc10", "epyc8"]})
        p = c / "autopilot/kit_wave.json"
        def mutate():
            cfg = json.loads(p.read_text()); cfg["dies"]["kv"]["gen_hosts"] = ["epyc10"]; p.write_text(json.dumps(cfg))
        with self.assertRaises(AssertionError):
            A.apply_marker(c, {"marker": cand(), "keep_gen_hosts": True}, "/x/old", "E0", pilot_item="t1", TC=self._tc([], mutate))
        d = json.loads(p.read_text())["dies"]["kv"]
        self.assertEqual(d["src"], "/x/old"); self.assertFalse((c / "lanes/handoff/tree_switch_kv.json").exists())

    def test_no_current_hosts_refuses(self):
        c = mk()
        with self.assertRaises(AssertionError):
            A.apply_marker(c, {"marker": cand(), "keep_gen_hosts": True}, "/x/old", "E0", pilot_item="t1", TC=self._tc([]))

    def test_default_still_uses_candidate_hosts(self):
        c = mk({"gen_hosts": ["epyc10", "epyc8"]})
        A.apply_marker(c, cand(), "/x/old", "E0", pilot_item="t1", TC=self._tc([]))
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["gen_hosts"], ["epyc10"])
