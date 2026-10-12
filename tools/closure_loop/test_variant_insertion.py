"""bf-insertion 2026-10-08: a route may start on an assumed insertion only when it was measured on the SAME variant."""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl

HOOKS = "export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/link_budget_hook.tcl'; "
ROUTE = "export OT_ORFS_CORNER_OVERRIDE=TC; {h}OUT={{RUN}}/routes SRC={{SRC}} BF_VAR={v} OT_MM_FF_SDC='a.sdc' " \
        "bash physical/s81_native_bf/margin/route_var.sh {{LABEL}} --hold-margin-ns {hm}{x}"


def spec(v, hm="0.000", x="", h=""):
    return {"name": "n", "block": "ot_s81_bf_native", "source": {"branch": "b", "commit": "c" * 40},
            "stages": {"calibrate": {"cmd": "cal"}, "route": {"cmd": ROUTE.format(v=v, hm=hm, x=x, h=h)}}}


class Key(unittest.TestCase):
    def test_hold_margin_and_paths_ignored(self):
        self.assertEqual(cl.variant_key(spec("recutcgl", "0.000")), cl.variant_key(spec("recutcgl", "0.010")))

    def test_variants_differ(self):
        ks = {cl.variant_key(spec("recutcgl")), cl.variant_key(spec("halfphl")), cl.variant_key(spec("recut")),
              cl.variant_key(spec("recut", x=" --param QZE=1")), cl.variant_key(spec("recut", x=" --param CG=0")),
              cl.variant_key(spec("recut", h=HOOKS))}
        self.assertEqual(len(ks), 6)


class Assume(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.st = Path(self.td.name)
        (self.st / "jobs").mkdir()
        self.p = patch.object(cl, "STATE", self.st)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.td.cleanup()

    def put(self, name, sp):
        (self.st / "jobs" / f"{name}.json").write_text(json.dumps({"name": name, "spec": sp}))

    def measured(self, job, **extra):
        e = dict(job=job, ss=dict(mean=1169, min=1145, max=1225), ff=dict(mean=714, min=693, max=758), **extra)
        (self.st / "measured_insertion.json").write_text(json.dumps({"blocks": {"ot_s81_bf_native": e}}))

    def j(self, sp):
        return {"name": "new", "spec": sp, "created": "2026-10-08T10:00:00-07:00"}   # pre CALIB-CORNER: SS assumption

    def test_other_variant_block_entry_rejected(self):
        self.put("bfh_recutcgl50", spec("recutcgl"))
        self.measured("bfh_recutcgl50")
        j = self.j(spec("halfphl"))
        env, src = cl.assumed_insertion(j)
        self.assertIsNone(env)
        self.assertIn("another variant", j["ins_assume_skip"])

    def test_same_variant_from_job_json(self):
        self.put("bfh_recutcgl50", spec("recutcgl", "0.010"))
        self.measured("bfh_recutcgl50")
        env, src = cl.assumed_insertion(self.j(spec("recutcgl", "0.000")))
        self.assertEqual((env["CK_SS_MEAN"], env["CK_FF_MEAN"]), (1169, 714))

    def test_variants_table(self):
        vk = cl.variant_key(spec("halfphl"))
        e = dict(job="x", ss=dict(mean=1546, min=1448, max=1569), ff=dict(mean=875, min=847, max=885))
        (self.st / "measured_insertion.json").write_text(json.dumps(
            {"blocks": {"ot_s81_bf_native": dict(e, job="other", variant="zzz")}, "variants": {vk: e}}))
        env, _ = cl.assumed_insertion(self.j(spec("halfphl")))
        self.assertEqual(env["CK_SS_MEAN"], 1546)
        env, _ = cl.assumed_insertion(self.j(spec("recut")))
        self.assertIsNone(env)


if __name__ == "__main__":
    unittest.main()
