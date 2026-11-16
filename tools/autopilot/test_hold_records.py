import copy, json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR  # noqa: E402
import kit_wave as KW  # noqa: E402

PLAN = "p" * 64


def base():
    return {"dies": {"s81": {"event": "B6gG3", "plan": "/x/B6gG3.json", "plan_sha256": PLAN, "planned_events": ["B6gG3b"],
                             "hold_event_items": {PLAN: ["col_a__t1", "col_a__t2", "col_b__t1", "ser_x"]}},
                     "hbm": {"event": "pEv11c", "plan_sha256": "h" * 64}}}


def rec(**k):
    r = {"id": "r1", "plan_sha": PLAN, "reason": "why", "release": ["event_adopt:B6gG3b"], "patterns": ["col_a__*"]}
    r.update(k)
    return r


class T(unittest.TestCase):
    def test_add_expands_pattern_on_compile(self):
        c = base()
        HR.add_record(c, "s81", rec())
        HR.compile_holds(c)
        self.assertEqual(list(c["dies"]["s81"]["hold_items"]), ["col_a__t1", "col_a__t2"])
        self.assertEqual(c["_hold_compiled"]["s81"]["col_a__t1"], "r1")

    def test_rejects_unknown_event_lane_and_free_text(self):
        for term in ("event_adopt:B6gG1d", "event_adopt:Event F", "lane_ready:HEAD-99", "lint_clean:nodie", "kit_snap:zz",
                     "input_staged:rel/x", "digest_changed:x", "event_adopt:B6g*"):
            with self.assertRaises(ValueError, msg=term):
                HR.add_record(base(), "s81", rec(release=[term]))

    def test_rejects_zero_match_unbound_and_empty(self):
        for bad in (rec(patterns=["nope*"]), rec(plan_sha=""), rec(patterns=[], items=[]), rec(reason="")):
            with self.assertRaises(ValueError):
                HR.add_record(base(), "s81", bad)

    def test_event_release_when_adopted(self):
        c = base()
        HR.add_record(c, "s81", rec())
        c["dies"]["s81"]["event"] = "B6gG3b"
        c["dies"]["s81"]["plan"] = "/x/B6gG3b.json"
        HR.compile_holds(c, HR.Ctx(event_met=KW._hold_term_met))
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})
        self.assertEqual(len(c["_hold_auto_released"]), 2)

    def test_lint_clean_is_per_item(self):
        c = base()
        HR.add_record(c, "s81", rec(release=["lint_clean:s81"]))
        c["dies"]["s81"]["_lint_clean"] = ["col_a__t1"]
        HR.compile_holds(c)
        self.assertEqual(list(c["dies"]["s81"]["hold_items"]), ["col_a__t2"])

    def test_digest_changed_and_staged_and_snap(self):
        c = base()
        HR.add_record(c, "s81", rec(release=["digest_changed"], digest="aaa"))
        HR.compile_holds(c, HR.Ctx(digest_fn=lambda cfg, die: "aaa"))
        self.assertEqual(len(c["dies"]["s81"]["hold_items"]), 2)
        c["dies"]["s81"]["hold_items"] = {}
        HR.compile_holds(c, HR.Ctx(digest_fn=lambda cfg, die: "bbb"))
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})
        c = base()
        HR.add_record(c, "s81", rec(release=["input_staged:/a/b", "kit_snap:hbm"]))
        HR.compile_holds(c, HR.Ctx(exists_fn=lambda p: True, kit_snap_fn=lambda cfg, die: False))
        self.assertEqual(len(c["dies"]["s81"]["hold_items"]), 2)           # all terms must be met
        c["dies"]["s81"]["hold_items"] = {}
        HR.compile_holds(c, HR.Ctx(exists_fn=lambda p: True, kit_snap_fn=lambda cfg, die: True))
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})

    def test_plan_sha_move_supersedes_or_follows(self):
        c = base()
        HR.add_record(c, "s81", rec())
        HR.add_record(c, "s81", rec(id="r2", patterns=["ser_*"], follow_plan=True))
        d = c["dies"]["s81"]
        d["plan_sha256"] = "n" * 64
        d["hold_event_items"]["n" * 64] = ["ser_x", "ser_y", "col_a__t1"]
        HR.compile_holds(c)
        self.assertEqual(sorted(d["hold_items"]), ["col_a__t1", "col_a__t2", "ser_x", "ser_y"])   # r1 keeps its old items, r2 rebound
        got = {(f["code"], f["id"]) for f in HR.audit(c)}
        self.assertIn(("HOLD-SUPERSEDED", "r1"), got)
        self.assertNotIn(("HOLD-SUPERSEDED", "r2"), got)

    def test_audit_unreachable_and_held_but_launched(self):
        c = base()
        c["dies"]["s81"]["hold_items"] = {"col_a__*": "old", "ser_x": "old2"}
        c["dies"]["s81"]["hold_release_on"] = {"col_a__*": "event_adopt:Event F", "ser_x": "lane_ready:X"}
        HR.migrate_cfg(c)
        HR.compile_holds(c)
        f = HR.audit(c, [("s81", "col_a__t9"), ("s81", "zzz")])
        codes = [(x["code"], x["n"]) for x in f]
        self.assertEqual(sorted(x["code"] for x in f), ["HELD-BUT-LAUNCHED", "TERM-UNREACHABLE", "TERM-UNREACHABLE"])
        self.assertEqual([x["items"] for x in f if x["code"] == "HELD-BUT-LAUNCHED"], [["col_a__t9"]])

    def test_migrate_keeps_effective_holds(self):
        c = base()
        d = c["dies"]["s81"]
        d["hold_items"] = {"a": "r1", "b": "r1", "c*": "r2", "d": "r1"}
        d["hold_release_on"] = {"a": "event_adopt:B6gG3", "b": "event_adopt:B6gG3", "c*": "lane_result:X + merge:abc", "zz": "merge:q"}
        old = KW.load_config(json.dumps(c))
        HR.migrate_cfg(c)
        self.assertEqual(len(c["dies"]["s81"]["hold_records"]), 3)
        new = KW.load_config(json.dumps(c))
        self.assertEqual(list(new["dies"]["s81"]["hold_items"].items()), list(old["dies"]["s81"]["hold_items"].items()))
        self.assertEqual(sorted(old["_hold_auto_released"]), sorted(new["_hold_auto_released"]))

    def test_convert_retypes_and_reports_unmapped(self):
        c = base()
        c["dies"]["s81"]["hold_items"] = {"a": "r", "b": "q"}
        c["dies"]["s81"]["hold_release_on"] = {"a": "event_adopt:B6gG3* (x) + lane_result:sdc_lint 0", "b": "lane_ready:Z"}
        HR.migrate_cfg(c)
        done, left = HR.convert_cfg(c, {"event_adopt:B6gG3* (x) + lane_result:sdc_lint 0": ["event_adopt:B6gG3b", "lint_clean:s81"]},
                                    {"s81": ["B6gG3c"]})
        self.assertEqual((done, [x[2] for x in left]), (1, ["lane_ready:Z"]))
        self.assertIn("b6gg3c", HR.known_events(c["dies"]["s81"]))
        with self.assertRaises(ValueError):
            HR.convert_cfg(c, {"lane_ready:Z": ["event_adopt:Nope1"]})

    def test_proof_and_census_terms(self):
        c = base()
        d = c["dies"]["s81"]
        for bad in ("proof:", "proof:a b", "census_lt:abc", "census_lt:"):
            with self.assertRaises(ValueError, msg=bad):
                HR.add_record(c, "s81", rec(release=[bad]))
        HR.add_record(c, "s81", rec(release=["proof:DRT0255", "census_lt:400k"]))
        HR.compile_holds(c, HR.Ctx(proof_fn=lambda n: n == "DRT0255", cells_fn=lambda die, i: 300000 if i == "col_a__t1" else 500000))
        self.assertEqual(list(d["hold_items"]), ["col_a__t2"])
        HR.compile_holds(c, HR.Ctx(proof_fn=lambda n: False, cells_fn=lambda die, i: 1))     # recompile is idempotent, proof unmet
        self.assertEqual(sorted(d["hold_items"]), ["col_a__t1", "col_a__t2"])
        HR.compile_holds(c, HR.Ctx(proof_fn=lambda n: True))                                 # cells unknown = held
        self.assertEqual(sorted(d["hold_items"]), ["col_a__t1", "col_a__t2"])

    def test_convert_keys_splits_records_and_drops(self):
        c = base()
        d = c["dies"]["s81"]
        d["hold_items"] = {"a": "r", "b": "r", "c": "r", "keep": "r"}
        d["hold_release_on"] = {k: "lane_ready:X" for k in d["hold_items"]}
        HR.migrate_cfg(c, only=["s81"])
        HR.convert_cfg(c, {}, {"s81": ["KV-HG1"]})
        self.assertEqual(HR.convert_keys(c, {"s81": {"a": ["event_adopt:KV-HG1"], "b": ["event_adopt:KV-HG1"], "c": None}}), (2, 1))
        HR.compile_holds(c)
        self.assertEqual(sorted(d["hold_items"]), ["a", "b", "keep"])
        self.assertEqual(sorted(r["id"] for r in d["hold_records"]), ["s81-mig-001", "s81-mig-001-k1"])
        with self.assertRaises(ValueError):
            HR.convert_keys(c, {"s81": {"zz": None}})
        with self.assertRaises(ValueError):
            HR.convert_keys(c, {"s81": {"keep": ["event_adopt:Nope1"]}})

    def test_migrate_only_one_die(self):
        c = base()
        c["dies"]["s81"]["hold_items"] = {"a": "r"}
        c["dies"]["hbm"]["hold_items"] = {"z": "r"}
        HR.migrate_cfg(c, only=["s81"])
        self.assertEqual(c["dies"]["hbm"]["hold_items"], {"z": "r"})
        self.assertNotIn("hold_records", c["dies"]["hbm"])


if __name__ == "__main__":
    unittest.main()
