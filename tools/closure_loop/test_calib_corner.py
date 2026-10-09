"""CALIB-CORNER 2026-10-08: TC routes calibrate at the route corner and reference the route IO SDC to the TT insertion."""
import json, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl
import ck_insertion as ck

NEW, OLD = "2026-10-08T20:00:00-07:00", "2026-10-08T15:00:00-07:00"
ENV = {f"CK_{c}_{a}{k}": v + d for c, v in (("SS", 770), ("TT", 581), ("FF", 420))
       for a in ("", "ALL_") for k, d in (("MEAN", 0), ("MIN", -90), ("MAX", 190))}


def job(created=NEW, **spec):
    s = {"name": "t", "block": "blk", "source": {"branch": "main", "commit": "c" * 40},
         "stages": {"calibrate": {"cmd": "echo cal", "base": "/b", "sdc_cmd": "mk.sh $CK_SS_MEAN"},
                    "route": {"cmd": "echo route"}}, **spec}
    return {"name": "t", "run": "/r", "host": "ot-epyc3", "spec": s, "commit_full": "c" * 40, "attempt": 1,
            "created": created}


def body(j, kind, cmd="echo x"):
    out = []

    def fake_ssh(host, c, input=None, **k):
        if input is not None:
            out.append(input)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "ship_helpers"), patch.object(cl, "is_local", lambda h: False):
        cl.launch_stage(j, {"kind": kind, "key": kind, "threads": 4}, cmd)
    return out[0]


class RouteEnv(unittest.TestCase):
    def test_tc_maps_tt(self):
        e = ck.route_env(ENV, "TC")
        self.assertEqual((e["CK_SS_MEAN"], e["CK_SS_MAX"], e["CK_SSLIB_MEAN"], e["CK_ROUTE_REF"]), (581, 771, 770, "TT"))
        self.assertEqual(e["CK_FF_MEAN"], 420)

    def test_ss_route_keeps_ss(self):
        e = ck.route_env(ENV, "")
        self.assertEqual((e["CK_SS_MEAN"], e["CK_ROUTE_REF"]), (770, "SS"))
        self.assertNotIn("CK_SSLIB_MEAN", e)

    def test_tc_without_tt_fails(self):
        with self.assertRaises(SystemExit):
            ck.route_env({k: v for k, v in ENV.items() if "_TT_" not in k}, "TC")


class Loop(unittest.TestCase):
    def test_route_ref(self):
        self.assertEqual(cl.route_ref(job()), "TT")
        self.assertIsNone(cl.route_ref(job(OLD)))                       # launched jobs keep their behaviour
        self.assertIsNone(cl.route_ref(job(route_corner="WC")))
        self.assertIsNone(cl.route_ref(job(route_ref="SS")))
        k = job(route_corner="keep")
        self.assertIsNone(cl.route_ref(k))
        k["spec"]["stages"]["route"]["cmd"] = "export OT_ORFS_CORNER_OVERRIDE=TC; run"
        self.assertEqual(cl.route_ref(k), "TT")

    def test_calibrate_env_and_tail(self):
        b = body(job(), "calibrate")
        self.assertIn("export OT_ORFS_CORNER=TC\n", b)
        self.assertIn("export OT_CAL_ROUTE_CORNER=TC\n", b)
        self.assertNotIn("OT_CAL_ROUTE_CORNER", body(job(OLD), "calibrate"))
        cal = next(x for x in cl.stage_list(job()["spec"]) if x["kind"] == "calibrate")
        self.assertIn('--route-corner "${OT_CAL_ROUTE_CORNER:-}"', cl.subst(cal["cmd"], job()))

    def test_assumed_insertion(self):
        with tempfile.TemporaryDirectory() as td:
            st = Path(td)
            blocks = {"blk": {"ss": {"mean": 770, "min": 700, "max": 800}, "ff": {"mean": 420, "min": 400, "max": 450},
                              "tt": {"mean": 581, "min": 488, "max": 768}, "grade": "routed", "job": "x",
                              "variant": cl.variant_key(job()["spec"])},     # bf-insertion: same-variant entries only
                      "nott": {"ss": {"mean": 770, "min": 700, "max": 800}, "ff": {"mean": 420, "min": 400, "max": 450}}}
            (st / "measured_insertion.json").write_text(json.dumps({"blocks": blocks}))
            with patch.object(cl, "STATE", st):
                env, src = cl.assumed_insertion(job())
                self.assertEqual((env["CK_SS_MEAN"], env["CK_SS_MIN"], env["CK_SS_MAX"]), (581, 488, 768))
                self.assertEqual((env["CK_SSLIB_MEAN"], env["CK_FF_MIN"], env["CK_ROUTE_REF"]), (770, 400, "TT"))
                self.assertIn("TT", src)
                env, _ = cl.assumed_insertion(job(OLD))
                self.assertEqual(env["CK_SS_MEAN"], 770)
                j = job()
                j["spec"]["block"] = "nott"
                self.assertEqual(cl.assumed_insertion(j), (None, None))   # no TT: sequential calibrate

    def test_record_measured_keeps_true_ss(self):
        with tempfile.TemporaryDirectory() as td:
            st = Path(td)
            j = job()
            j["calibration"] = {"env": ck.route_env(ENV, "TC"), "clock": "ck", "parasitics": "p"}
            with patch.object(cl, "STATE", st):
                cl.record_measured(j)
            b = json.loads((st / "measured_insertion.json").read_text())["blocks"]["blk"]
            self.assertEqual((b["ss"]["mean"], b["tt"]["mean"], b["route_ref"]), (770, 581, "TT"))


if __name__ == "__main__":
    unittest.main()
