"""PREROUTE-GATE 2026-10-08: pre-route timing gate (tools/preroute_gate.py) and its closure-loop wiring."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import closure_loop as cl  # noqa: E402
import orfs_hold_mm as H  # noqa: E402
import preroute_gate as G  # noqa: E402
from test_fp_lint import run_launch  # noqa: E402


def dump(period=833.333, **classes):
    """classes: name -> (ws, {bin: n}); bins are 25 ps"""
    return {"period_ps": period, "bin_ps": 25.0, "truncated": False,
            "classes": {k: {"ws_ps": ws, "endpoints": sum(h.values()), "hist": {str(b): n for b, n in h.items()},
                            "worst": [{"slack_ps": ws, "start": "a", "end": "b"}]} for k, (ws, h) in classes.items()}}


class Judge(unittest.TestCase):
    def test_worst_closure_passes(self):
        # ha2_truecredit_tx_reg (CLOSED at TT): reg2reg -314.9 ps placed, 561 endpoints below 0
        self.assertEqual(G.judge(dump(reg2reg=(-314.9, {-13: 20, -5: 300, -1: 241})))[0], "PASS")

    def test_hopeless_macro_fails(self):
        # hbm_hc_quarter: macro WNS -1859, thousands of endpoints far below
        v, reasons, m = G.judge(dump(macro=(-1859.1, {-75: 3000, -40: 7000}), reg2reg=(-117.7, {-5: 1})))
        self.assertEqual(v, "FAIL")
        self.assertTrue(reasons[0].startswith("macro WNS -1859.1"))

    def test_few_endpoints_pass(self):
        self.assertEqual(G.judge(dump(reg2reg=(-1500.0, {-60: 10})))[0], "PASS")

    def test_io_never_gated(self):
        self.assertEqual(G.judge(dump(io=(-3000.0, {-120: 5000})))[0], "PASS")

    def test_route_period_normalised(self):
        # at a 730 ps route, raw -850 is -746.7 at sign-off: above -750, passes
        d = dump(730.0, reg2reg=(-850.0, {-35: 500}))
        self.assertEqual(G.judge(d)[2]["reg2reg"]["ws_ps"], -746.7)
        self.assertEqual(G.judge(d)[0], "PASS")

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "d.json"
            p.write_text(json.dumps(dump(macro=(-1859.1, {-75: 3000}))))
            self.assertEqual(G.main(["check", str(p), "--out", str(Path(td) / "r.json")]), 3)
            self.assertEqual(json.loads((Path(td) / "r.json").read_text())["verdict"], "FAIL")
            self.assertEqual(G.main(["check", str(p), "--warn-only"]), 0)
            self.assertEqual(G.main(["check", str(p), "--set", "ws_ps=-2000"]), 0)
            self.assertEqual(G.main(["check", str(Path(td) / "missing.json")]), 2)


class LoopWiring(unittest.TestCase):
    def test_default_on_for_route_only(self):
        b = run_launch({})
        self.assertIn("export OT_PREROUTE_GATE=1 OT_PREROUTE_GATE_ARGS=''", b)
        self.assertIn("preroute_gate.py preroute_gate.tcl", b)                 # shipped into src/tools
        self.assertIn("-e OT_PREROUTE_GATE -e OT_PREROUTE_GATE_ARGS", b)        # the docker shim passes it
        self.assertNotIn("OT_PREROUTE_GATE=1", run_launch({}, "calibrate"))
        self.assertIn("../preroute_gate.py", cl.HELPERS)

    def test_opt_out_and_overrides(self):
        self.assertNotIn("OT_PREROUTE_GATE=1", run_launch({"preroute_gate": False}))
        b = run_launch({"preroute_gate": {"set": {"ws_ps": -900}}})
        self.assertIn("OT_PREROUTE_GATE_ARGS='--set ws_ps=-900'", b)

    def test_gate_without_fp_lint_still_mounts(self):
        b = run_launch({"fp_lint": False})
        self.assertNotIn("export OT_FP_LINT=1", b)
        self.assertIn("export OT_FP_LINT_DIR=/r/cl/fplint/route.a1", b)
        self.assertIn("OT_PREROUTE_GATE=1", b)
        self.assertNotIn("export OT_FP_LINT_DIR", run_launch({"fp_lint": False}, "calibrate"))

    def test_crash_becomes_preroute_margin(self):
        j = {"name": "t", "run": "/r", "host": "ot-epyc3", "stage_tag": "route.a1", "attempt": 1, "retries_used": 0,
             "spec": {"verdict": {}}, "status": "RUNNING"}
        fail = "preroute_gate: FAIL: macro ws -1859.1\nPREROUTE_MARGIN: macro WNS -1859.1 ps at 833.333"
        done = {}

        def fake_ssh(host, c, **k):
            return SimpleNamespace(returncode=0, stdout=fail if "fplint/route.a1/PREROUTE_FAIL" in c else "", stderr="")

        def fake_finish(j, status, reason, text):
            done.update(status=status, reason=reason, text=text)
        with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "finish", fake_finish), \
                patch.object(cl, "kill_own_stage", lambda j: done.setdefault("killed", True)):
            cl.crash(j, {"kind": "route", "key": "route"}, None, "rc=1")
        self.assertEqual(done["status"], "PREROUTE_MARGIN")
        self.assertTrue(done["reason"].startswith("macro WNS -1859.1"))
        self.assertTrue(done.get("killed"))
        self.assertIn("PREROUTE_MARGIN", cl.TERMINAL)


class OrfsHook(unittest.TestCase):
    def test_patch_installs_post_detail_place_hook(self):
        with tempfile.TemporaryDirectory() as td:
            u = Path(td) / "util.tcl"
            u.write_text("proc source_step_tcl { hook_type step_name } {\n" + H.FPL_ANCHOR + "}\n")
            self.assertEqual(H.patch_preroute_gate(Path(td)), "patched")
            self.assertEqual(H.patch_preroute_gate(Path(td)), "already patched")
            t = u.read_text()
            self.assertIn('$step_name eq "DETAIL_PLACE"', t)
            self.assertEqual(len(re.findall("ot_preroute_gate_flow", t)), 1)


if __name__ == "__main__":
    unittest.main()
