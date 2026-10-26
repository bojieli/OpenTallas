"""METHODOLOGY 12.1c / 12.4d / 12.4e (v2, owner 10-26): die-top signal GRT on M4-M7 + leftover M8/M9 by default,
PG IR closed before signal GRT, skew gate re-run after signal GRT."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_infra as DI  # noqa: E402

GRT_TCL = ("read_verilog /work/grt/route.v\nsource /work/grt/obs.tcl\nset_routing_layers -signal M4-M7\n"
           "set_global_routing_layer_adjustment M4 0.75\nset_global_routing_layer_adjustment M8 0.4\n"
           "set_global_routing_layer_adjustment M9 0.4\n"
           "global_route -congestion_iterations 50 -congestion_report_file /work/grt/congestion.rpt\n"
           "write_guides /work/grt/route.guide\n")


class GrtLayers(unittest.TestCase):
    def _run(self, td, pg_ir="PASS", **kw):
        d = Path(td)
        kit, pre, out = d / "kit", d / "pre", d / "out"
        (kit / "grt").mkdir(parents=True)
        pre.mkdir()
        (kit / "grt" / "grt.tcl").write_text(GRT_TCL)
        (kit / "grt" / "route.v").write_text("module x(); endmodule\n")
        pg = d / "pg.json"
        pg.write_text(json.dumps({"ir_verdict": pg_ir}))
        (pre / "preroute.json").write_text(json.dumps({"pg_file": str(pg)}))
        a = SimpleNamespace(iterations=50, plan="p", kit=str(kit), pre=str(pre), out=str(out), pg=None, m89=False,
                            m47_only=False, pg_ir_open_trial=False, mem=64)
        for k, v in kw.items():
            setattr(a, k, v)
        with mock.patch.object(DI, "load_plan", return_value=None), mock.patch.object(DI, "base_obs", return_value=""):
            DI.cmd_grt(a)
        return out, pg

    def test_default_opens_leftover_m8_m9(self):
        with tempfile.TemporaryDirectory() as td:
            out, _ = self._run(td)
            t = (out / "grt.tcl").read_text()
            self.assertIn("set_routing_layers -signal M4-M9", t)
            self.assertNotIn("-signal M4-M7", t)
            self.assertNotIn("M8 0.4", t)            # the pre-route obstructions are the taken capacity
            self.assertIn("set_global_routing_layer_adjustment M8 0\n", t)
            self.assertIn("12.1c", (out / "grt_meta.json").read_text())

    def test_m47_only_is_legacy_diagnostic(self):
        with tempfile.TemporaryDirectory() as td:
            out, _ = self._run(td, m47_only=True)
            self.assertIn("-signal M4-M7", (out / "grt.tcl").read_text())
            self.assertIn("LEGACY", (out / "grt_meta.json").read_text())

    def test_pg_ir_must_close_before_signal_grt(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "12.4e"):
                self._run(td, pg_ir="FAIL")
        with tempfile.TemporaryDirectory() as td:
            out, _ = self._run(td, pg_ir="FAIL", pg_ir_open_trial=True)
            self.assertTrue(json.loads((out / "grt_meta.json").read_text())["trial"])

    def test_pg_growth_after_grt_and_post_signal_skew_gate(self):
        with tempfile.TemporaryDirectory() as td:
            out, pg = self._run(td)
            (out / "grt.log").write_text("Final congestion report\n M4 100 1 1.0% 0 / 0 / 0\n"
                                         " Total 100 1 1.0% 0 / 0 / 0\nEXIT 0\n")
            d = Path(td)
            for name, verdict in (("clk", "PASS"), ("post", "FAIL")):
                (d / name).mkdir()
                (d / name / "clock_report.json").write_text(json.dumps(
                    {"corners": {c: {"related_pair_max_ps": 70.0, "verdict": verdict} for c in ("TT", "FF")}}))
            (d / "pre" / "preroute.json").write_text(json.dumps({"tracks_taken": {"M8": {"all": 0.1}}}))
            a = SimpleNamespace(pre=str(d / "pre"), grt=[str(out)], clock=str(d / "clk"), clock_post=str(d / "post"),
                                pg=None, sites=None, out=str(d / "rep.json"))
            DI.cmd_report(a)
            r = json.loads((d / "rep.json").read_text())
            self.assertEqual(r["freeze_gate"]["verdict"], "FAIL")        # post-signal skew fails
            self.assertTrue(r["freeze_gate"]["signal_grt0"])
            pg.write_text(json.dumps({"ir_verdict": "PASS", "grid": "grown"}))   # PG grows after the signal GRT
            a.clock_post = str(d / "clk")
            DI.cmd_report(a)
            r = json.loads((d / "rep.json").read_text())
            self.assertFalse(r["grt"][str(out)]["pg_unchanged_since_grt"])
            self.assertFalse(r["freeze_gate"]["signal_grt0"])
            self.assertEqual(r["freeze_gate"]["verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main()
