"""HOLD-FLOW-R 11-16: the standard hold_eco step (OT_PRD_HOLD_TARGETED=1): in-session planner parity, wiring, eco_loop policy."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "post_route_drv"))
sys.path.insert(0, str(HERE.parent))
import hold_eco_internal as H  # noqa: E402
import eco_loop  # noqa: E402

PLAN = HERE / "post_route_drv/hold_eco_internal_plan.tcl"
OPENROAD = os.environ.get("OPENROAD_BIN") or shutil.which("openroad")


def tcl(script):
    r = subprocess.run(["tclsh"], input=script, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.split()


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class Parity(unittest.TestCase):
    def test_sizing_matches_the_python_planner(self):
        needs = [0, -3, 1, 10, 24.9, 25, 25.01, 29.8, 30, 59.7, 68.19, 100, 500]
        src = "set f [open %s]; set t [read $f]; close $f; eval [string range $t [string first {proc ot_hei_size} $t] [string first {proc ot_hei_capture_pin} $t]-1]\n" % PLAN
        got = tcl(src + "".join(f"puts [ot_hei_size {n}]\n" for n in needs))
        self.assertEqual([int(x) for x in got], [H.need_to_cells(n) for n in needs])

    def test_afford_matches_the_python_cut(self):
        src = "set f [open %s]; set t [read $f]; close $f; eval [string range $t [string first {proc ot_hei_size} $t] [string first {proc ot_hei_capture_pin} $t]-1]\n" % PLAN
        for tt in (-50, -42, 80, 100, 132.8, 175, 330, 458.69, 600):
            want = H.plan(H.read_endpoints("endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\ttt_setup_slack_ps\n"
                                           f"u/a/D\ts\treg\treg\t-300\t{tt}\n"))
            n_py = dict(want["cells"]).get("u/a/D", 0)
            n_tcl = min(int(tcl(src + f"puts [ot_hei_afford {tt} 132.8 -42.0]\n")[0]), H.need_to_cells(310))
            self.assertEqual(n_tcl, n_py, tt)


class Wiring(unittest.TestCase):
    def test_hook_runs_the_planner_before_the_insert(self):
        hook = (HERE / "post_route_drv/prd_hook.tcl").read_text()
        i = hook.index("OT_PRD_HOLD_TARGETED")
        seg = hook[i:i + 1800]
        self.assertLess(seg.index("hold_eco_internal_plan.tcl"), seg.index("hold_eco_internal_insert.tcl"))
        self.assertIn("-scenes BC", seg)
        self.assertIn("ot_mm_unsync", seg)
        mk = (HERE / "post_route_drv/prd_mk.sh").read_text()
        self.assertIn("hold_eco_internal_plan.tcl", mk)
        self.assertIn("OT_PRD_HOLD_TARGETED=1", mk)
        run = (HERE / "post_route_drv/prd_run.sh").read_text()
        self.assertIn("-e OT_PRD_HOLD_TARGETED=", run)
        self.assertIn("OT_PRD_HOLD_TARGETED=0;", run)             # a stray export never leaks into a pinned pass dir

    def test_eco_loop_enables_it_for_hold_only_cases_only(self):
        self.assertTrue(hasattr(eco_loop, "targeted_hold_case"))
        with tempfile.TemporaryDirectory() as d:
            import json
            rec = {"checks": {"drc": {"verdict": "PASS", "count": 0}, "setup_tt": {"verdict": "PASS"}, "hold_ff": {"verdict": "FAIL", "wns_ps": -20, "violators": 30}},
                   "profile_gates": {"drc": "PASS", "setup_tt": "PASS", "hold_ff": "FAIL"}}
            p = Path(d) / "signoff.json"
            p.write_text(json.dumps(rec))
            orig = eco_loop.minimal_hold_only
            try:
                eco_loop.minimal_hold_only = lambda r: True
                self.assertTrue(eco_loop.targeted_hold_case(p))
                eco_loop.minimal_hold_only = lambda r: False                    # setup also fails: global repair as before
                self.assertFalse(eco_loop.targeted_hold_case(p))
                eco_loop.minimal_hold_only = lambda r: True
                os.environ["OT_ECO_HOLD_TARGETED"] = "0"
                self.assertFalse(eco_loop.targeted_hold_case(p))
            finally:
                os.environ.pop("OT_ECO_HOLD_TARGETED", None)
                eco_loop.minimal_hold_only = orig
        self.assertIn('env["OT_PRD_HOLD_TARGETED"] = "1"', (HERE / "eco_loop.py").read_text())


@unittest.skipUnless(OPENROAD, "OpenROAD required")
class AutoPlanSta(unittest.TestCase):
    def test_port_paths_get_no_cells_internal_ones_do(self):
        sys.path.insert(0, str(HERE.parent))
        import test_cts_hold_scope as C
        import test_nonport_scope_sta as F
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "f.lib").write_text(F.LIB)
            (d / "f.lef").write_text(F.LEF)
            (d / "f.v").write_text(C.NETLIST)
            s = (f"read_lef {d}/f.lef\nread_liberty {d}/f.lib\nread_verilog {d}/f.v\nlink_design top\n"
                 "create_clock -name clk -period 0.833 [get_ports CK]\nset_clock_uncertainty -hold 0.2 [get_clocks clk]\n"
                 "set_input_delay -clock clk -min -0.02 [get_ports DIN*]\nset_input_delay -clock clk -max 0.1 [get_ports DIN*]\n"
                 "set_output_delay -clock clk -min 0 [all_outputs]\nset_output_delay -clock clk -max 0.1 [all_outputs]\n"
                 f"source {PLAN}\nset n [ot_hei_auto_plan {{}} {{}} {d}/plan.tsv]\nputs \"AUTO n=$n\"\nexit\n")
            (d / "t.tcl").write_text(s)
            p = subprocess.run([OPENROAD, "-no_init", "-exit", str(d / "t.tcl")], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            rows = H.read_plan((d / "plan.tsv").read_text())
            names = [e for e, _ in rows]
            self.assertFalse([e for e in names if e.startswith("u_in") or e.startswith("u_a/")], names)   # fed by input ports
            self.assertTrue(names and all(e in ("u_b/D", "u_c/D") for e in names), names)
            self.assertTrue(all(1 <= n <= 4 for _, n in rows))


if __name__ == "__main__":
    unittest.main()
