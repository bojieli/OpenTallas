import hashlib, json, tempfile, unittest
from pathlib import Path
import kit_wave as K

SHA = "a" * 64

class GenPilotReceipt(unittest.TestCase):
    def setup_case(self):
        root = Path(tempfile.mkdtemp())
        path = root / "a1"
        path.mkdir()
        sp = {"die": "s81", "item": "t1", "src": "/tree/current", "src_manifest_hash": SHA}
        file = path / "spec.json"
        file.write_text(json.dumps(sp))
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        stages = {stage: 0 for stage in K.GEN_PILOT_STAGES}
        cfg = {"dies": {"s81": {"hold_records": [{"auto_pilot": True, "pilot_items": ["t1"]}]}}}
        state = {"items": {"x": {"die": "s81", "item": "t1", "dir": str(path), "status": "RUNNING"}}}
        return path, file, sp, digest, stages, cfg, state

    def test_actual_gen_boundary_credits_running_pilot_without_place(self):
        path, file, sp, digest, stages, cfg, state = self.setup_case()
        self.assertTrue(K.publish_gen_pilot_receipt(file, digest, stages))
        self.assertFalse((path / "result.json").exists())
        self.assertEqual(K.pilot_passed_map(state, cfg), {"s81": [SHA[:12]]})
        self.assertTrue(K.publish_gen_pilot_receipt(file, digest, stages))

    def test_failed_missing_or_advisory_stage_never_publishes(self):
        for stage in (*K.GEN_PILOT_STAGES, "kit_topology"):
            path, file, sp, digest, stages, cfg, state = self.setup_case()
            stages[stage] = 2
            self.assertFalse(K.publish_gen_pilot_receipt(file, digest, stages), stage)
            self.assertFalse((path / "gen_pilot.json").exists())
            self.assertEqual(K.pilot_passed_map(state, cfg), {})
        path, file, sp, digest, stages, cfg, state = self.setup_case()
        del stages["preflight"]
        self.assertFalse(K.publish_gen_pilot_receipt(file, digest, stages))

    def test_mutated_spec_is_refused_at_publication_and_consumption(self):
        path, file, sp, digest, stages, cfg, state = self.setup_case()
        file.write_text(json.dumps(dict(sp, src="/different")))
        self.assertFalse(K.publish_gen_pilot_receipt(file, digest, stages))
        file.write_text(json.dumps(sp))
        self.assertTrue(K.publish_gen_pilot_receipt(file, digest, stages))
        file.write_text(json.dumps(dict(sp, src_manifest_hash="b" * 64)))
        self.assertEqual(K.pilot_passed_map(state, cfg), {})

    def test_incomplete_or_foreign_receipt_is_not_overwritten_or_credited(self):
        path, file, sp, digest, stages, cfg, state = self.setup_case()
        target = path / "gen_pilot.json"
        target.write_text("{incomplete")
        self.assertFalse(K.publish_gen_pilot_receipt(file, digest, stages))
        self.assertEqual(target.read_text(), "{incomplete")
        self.assertEqual(K.pilot_passed_map(state, cfg), {})
        target.unlink()
        self.assertTrue(K.publish_gen_pilot_receipt(file, digest, stages))
        rec = json.loads(target.read_text())
        rec["item"] = "other"
        target.write_text(json.dumps(rec))
        self.assertEqual(K.pilot_passed_map(state, cfg), {})

    def test_prepublication_dry_gen_is_not_a_live_source_pilot(self):
        path, file, sp, digest, stages, cfg, state = self.setup_case()
        sp["dry_gen"] = True
        file.write_text(json.dumps(sp))
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        self.assertFalse(K.publish_gen_pilot_receipt(file, digest, stages))
        self.assertFalse((path / "gen_pilot.json").exists())
        self.assertEqual(K.pilot_passed_map(state, cfg), {})

    def test_kit_rtl_canary_failed_stage_never_publishes(self):
        path, file, sp, digest, stages, cfg, state = self.setup_case()
        stages["kit_rtl"] = 3
        self.assertFalse(K.publish_gen_pilot_receipt(file, digest, stages))
        self.assertFalse((path / "gen_pilot.json").exists())

    def test_kit_rtl_canary_receipt_carries_the_verdict(self):
        path, file, sp, digest, stages, cfg, state = self.setup_case()
        stages["kit_rtl"] = 0
        self.assertTrue(K.publish_gen_pilot_receipt(file, digest, stages))
        rec = json.loads((path / "gen_pilot.json").read_text())
        self.assertEqual((rec["stages"]["kit_rtl"], rec["canary"]), (0, "kit_rtl_v1"))

    def test_canary_mark_without_kit_rtl_stage_fails_for_a_kit_rtl_recipe_only(self):
        rec = {"canary": "kit_rtl_v1", "stages": {"gen": 0}}
        self.assertFalse(K.kit_rtl_canary_ok(rec, {"kit_rtl": {"mode": "bind"}}))
        self.assertFalse(K.kit_rtl_canary_ok(rec, {"kit_rtl": {"script": "/x.sh"}}))
        self.assertTrue(K.kit_rtl_canary_ok(rec, {"kit_rtl": {}}))                      # no kit_rtl stage in this recipe
        self.assertTrue(K.kit_rtl_canary_ok({"stages": {"gen": 0}}, {"kit_rtl": {"mode": "bind"}}))   # legacy receipt: grandfathered
        self.assertFalse(K.kit_rtl_canary_ok({"stages": {"kit_rtl": 2}}, {}))
        self.assertTrue(K.kit_rtl_canary_ok({"stages": {"kit_rtl": 0}}, {}))

