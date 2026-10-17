"""tools/ref_tile/rekit_native_launch.py: a CLOSED recipe-1 / early recipe-2 kit is re-kitted with the recipe-2 output stage
at the same outline, and the job's reroute_reason passes the closure loop's CLOSED_STANDS gate."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "closure_loop"))
import ref_tile as RT  # noqa: E402
import rekit_native_launch as NL  # noqa: E402

EX = HERE / "examples"


def closed(recipe=1, **kw):
    s = RT.load_spec(str(EX / "nhb_pbst_ref.json"))
    s.update(kw)
    RT.apply_recipe(s, recipe)
    if recipe == 2:          # an early recipe-2 kit (before 36de4b87f): pin stage, but no split / HB2 / kept pin regs
        for k in ("pin_reg_split", "keep_pin_regs", "hold_pad"):
            s.pop(k, None)
    return s


def assessed(s, recipe):
    return {"cell": "nhb", "design": "qwen", "view": f"{RT.kit_dir(s)}/views/x", "launch_ps": 331.4, "launch_over": 9,
            "capture_ps": 150.0, "job": "nhb_pbst_ref-r1-aaaaaaaaa", "kit": RT.kit_dir(s), "commit": "a" * 40,
            "recipe": recipe, "spec": s, "verdict": "REKIT"}


class Rekit(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        p = patch.multiple(NL, JOBS=Path(self.td.name), INTAKE=Path(self.td.name))
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.td.cleanup)

    def regen(self, s, recipe, die=(0, 0, 151.2, 146.88)):
        fp = json.dumps({"die": list(die)})
        with patch.object(NL, "show", lambda c, path: fp if path.endswith("floorplan.json") else None):
            ns = NL.new_spec(assessed(s, recipe))
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(ns, f)
        chk = RT.load_spec(f.name)
        RT.apply_recipe(chk, RT.kit_recipe(chk, None, f.name))
        return ns, chk, RT.gen(f.name, write=False)

    def test_recipe1_kit_gets_the_output_stage_and_keeps_its_geometry(self):
        s = closed(1)
        ns, chk, r = self.regen(s, 1)
        self.assertIsNone(NL.output_stage_ok(chk))
        self.assertEqual(r["outline"], [151.2, 146.88])                      # the closed die, not a re-derived one
        self.assertEqual(chk["route"]["macro_halo_um"], RT.HALO_UM)          # recipe-1 halo / hold margin stand
        self.assertEqual(chk["route"]["hold_margin_ns"], 0.010)
        self.assertEqual(chk["pins"], s["pins"])
        self.assertEqual(ns["reroute_reason"]["kind"], "native_launch")
        self.assertEqual(ns["job"]["tag"], "nl1")
        job = RT.gen_job(chk, RT.kit_dir(chk), "b" * 9, [])
        self.assertEqual(job["reroute_reason"]["launch_ps"], 331.4)
        self.assertIn("structural_change", job)

    def test_early_recipe2_kit_gets_split_hb2_and_kept_regs(self):
        s = closed(2)
        self.assertIsNotNone(NL.output_stage_ok(s))                          # the closed kit lacks the stage
        _, chk, _ = self.regen(s, 2)
        self.assertIsNone(NL.output_stage_ok(chk))
        if RT.RECIPE_LATEST >= 4:      # FLOW-HOLD recipe 4: flop-first pins, no pads
            self.assertEqual(chk["hold_budget"], "die")
            self.assertFalse(chk.get("inhold") or chk.get("outhold"))
            self.assertTrue(chk["keep_pin_regs"])
        else:
            self.assertEqual(chk["hold_pad"]["cell"], RT.RECIPE_HOLD_PAD)
            self.assertTrue(chk["pin_reg_split"] and chk["keep_pin_regs"])

    def test_job_tag_skips_used_names(self):
        (Path(self.td.name) / "nhb_pbst_ref-nl1-aaaaaaaaa.json").write_text("{}")
        ns, _, _ = self.regen(closed(1), 1)
        self.assertEqual(ns["job"]["tag"], "nl2")

    def test_live_jobs_ignore_ingested_intake_specs(self):
        d = Path(self.td.name)
        (d / "j1.json").write_text(json.dumps({"status": "CLOSED", "spec": {"block": "b"}}))
        (d / "j2.json").write_text(json.dumps({"status": "RUNNING", "spec": {"block": "b"}}))
        self.assertEqual(NL.live_jobs_of("b"), ["j2"])


if __name__ == "__main__":
    unittest.main()
