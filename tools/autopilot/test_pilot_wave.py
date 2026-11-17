import json, os, tempfile, unittest
import hold_records as HR
import kit_wave as KW

SHA = "35eaaa5d65dae530b163ca2fba251d2dfd309006d6b61ab22fa126e79cdaea59"


def cfg0(**d):
    base = {"src": "/x/old", "plan_sha256": "p1", "hold_records": [{"release": ["tree_ready:s81:/x/new"]}], "gen_hosts": ["epyc10"]}
    base.update(d)
    return {"dies": {"s81": base}, "_item_names": {"s81": ["t9", "t1", "t5"]}}


def ctx(**kw):
    return type("C", (), {"tree_fn": staticmethod(lambda d, t: True), "marker_fn": staticmethod(lambda d: {"manifest_hash": SHA}), **kw})()


class Pilot(unittest.TestCase):
    def test_switch_adds_one_pilot_hold_naming_the_manifest(self):
        cfg = cfg0()
        out = HR.apply_tree_switches(cfg, ctx())
        self.assertIn("pilot_hold", out[0][2])
        r = [x for x in cfg["dies"]["s81"]["hold_records"] if x.get("auto_pilot")][0]
        self.assertEqual(r["release"], ["gen_pilot:s81:35eaaa5d65da"])
        self.assertEqual(r["pilot_items"], ["t1"])                    # smallest item name
        self.assertEqual(r["items"], ["*"])
        self.assertEqual(HR.validate_record(dict(r, die="s81"), cfg), [])
        HR.apply_tree_switches(cfg, ctx())                             # idempotent (src already switched)
        self.assertEqual(len([x for x in cfg["dies"]["s81"]["hold_records"] if x.get("auto_pilot")]), 1)

    def test_compile_holds_all_but_the_pilot_until_it_passes(self):
        cfg = cfg0(pilot_item="t5")
        HR.apply_tree_switches(cfg, ctx())
        HR.compile_holds(cfg, HR.Ctx())
        held = set(cfg["dies"]["s81"]["hold_items"])
        self.assertEqual(held, {"t1", "t9"})                           # t5 = the pilot launches, the rest wait
        HR.compile_holds(cfg, HR.Ctx(pilot_fn=lambda die, sha: (die, sha) == ("s81", "35eaaa5d65da")))
        self.assertEqual(set(cfg["dies"]["s81"].get("hold_items") or {}), set())
        HR.compile_holds(cfg, HR.Ctx(pilot_fn=lambda die, sha: (die, sha) == ("s81", "deadbeefdead")))      # another tree's pilot does not release
        self.assertEqual(set(cfg["dies"]["s81"]["hold_items"]), {"t1", "t9"})

    def test_fails_open_without_a_pilot_item_or_when_disabled(self):
        for cfg in (dict(cfg0(), _item_names={}), cfg0(pilot_after_switch=False)):
            HR.apply_tree_switches(cfg, ctx())
            self.assertFalse([x for x in cfg["dies"]["s81"]["hold_records"] if x.get("auto_pilot")])

    def test_term_validation(self):
        cfg = cfg0()
        self.assertIsNone(HR.term_error("gen_pilot:s81:35eaaa5d65da", "s81", cfg))
        self.assertIsNotNone(HR.term_error("gen_pilot:s81:short", "s81", cfg))
        self.assertIsNotNone(HR.term_error("gen_pilot:qwen_kvsys:35eaaa5d65da", "s81", cfg))
        self.assertIsNone(HR.unreachable_why("gen_pilot:s81:35eaaa5d65da", "s81", cfg))

    def test_pilot_passed_map_reads_the_attempt_spec(self):
        d = tempfile.mkdtemp(); json.dump({"src_manifest_hash": SHA}, open(d + "/spec.json", "w"))
        cfg = cfg0(); HR.apply_tree_switches(cfg, ctx()); cfg["dies"]["s81"]["hold_records"][-1]["pilot_items"] = ["t1"]
        st = {"items": {"a": {"die": "s81", "item": "t1", "status": "PASS", "dir": d}, "b": {"die": "s81", "item": "t9", "status": "PASS", "dir": d}}}
        self.assertEqual(KW.pilot_passed_map(st, cfg), {"s81": ["35eaaa5d65da"]})
        st["items"]["a"]["status"] = "FAIL"
        self.assertEqual(KW.pilot_passed_map(st, cfg), {})
