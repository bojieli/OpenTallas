"""CLOSURE-STRATEGY lever 7 (HOLD-FLOW-R 11-17): post-place built-wire check of zero-logic register-to-register paths."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "post_route_drv"))
TCL = HERE / "place_wire_ratio.tcl"
OPENROAD = os.environ.get("OPENROAD_BIN")
IMAGE = "openroad/orfs:asap7lock"


def openroad_cmd(tmp):
    """the pinned ORFS image (the distro reader crashes on this fixture: hold_capture_net uses the same rule), else OPENROAD_BIN"""
    if OPENROAD:
        return [OPENROAD]
    docker = shutil.which("docker")
    if docker and subprocess.run([docker, "image", "inspect", IMAGE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        return [docker, "run", "--rm", "--network", "none", "-v", f"{HERE.parents[1]}:{HERE.parents[1]}:ro", "-v", f"{tmp}:{tmp}",
                IMAGE, "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"]
    return None


def tcl(script):
    src = TCL.read_text()
    body = src[:src.index("proc pwr_env")]                      # the pure evaluator only (no OpenDB)
    r = subprocess.run(["tclsh"], input=body + script, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class Rule(unittest.TestCase):
    def test_qc_cb_class_fails_and_s81_t47_classes_pass(self):
        out = tcl('puts [pwr_eval {{cb 280 1740} {t47a 500 515} {t47b 500 940} {short 50 400}} 400 3.0]')
        self.assertIn("cb 280 1740 6.214", out)                 # QC cb: ratio 6.2
        self.assertNotIn("t47a", out)                           # 1.03
        self.assertNotIn("t47b", out)                           # 1.88
        self.assertNotIn("short", out)                          # ratio 8 but not longer than 400 um

    def test_both_conditions_are_needed(self):
        self.assertEqual(tcl('puts [llength [pwr_eval {{x 100 399} {y 100 401}} 400 3.0]]'), "1")        # 399 is not > 400 um; 401 / 100 = 4.01
        self.assertEqual(tcl('puts [llength [pwr_eval {{x 100 399} {z 200 1200} {w 200 600}} 400 3.0]]'), "1")   # w: ratio exactly 3 passes

    def test_worst_first_and_zero_direct(self):
        out = tcl('puts [pwr_eval {{a 100 500} {b 100 900} {c 0 500}} 400 3.0]')
        self.assertTrue(out.startswith("{c 0 500"))              # a loop (direct 0) is the worst detour
        self.assertLess(out.index("b 100 900"), out.index("a 100 500"))

    def test_wiring(self):
        gate = (HERE / "gp_noconverge_gate.tcl").read_text()
        self.assertIn("place_wire_ratio.tcl", gate)
        self.assertIn("place_wire_ratio.tcl", (HERE / "core_input_chain.tcl").read_text())
        gen = (HERE / "gen_phys.py").read_text()
        self.assertGreaterEqual(gen.count("place_wire_ratio.tcl"), 2)
        src = TCL.read_text()
        for needle in ("OT_PLACE_WIRE_RATIO", "FAIL_PLACE_WIRE_RATIO", "OT_PLACE_WIRE_MIN_UM", "OT_PLACE_WIRE_RATIO_MAX"):
            self.assertIn(needle, src)
        self.assertIn('pwr_env OT_PLACE_WIRE_RATIO report', src)    # report-only by default


LIB_THRESH = "\n".join(f"{k}_threshold_pct_{e} : 50;" for k in ("input", "output") for e in ("rise", "fall")) + "\n" + \
    "\n".join(f"slew_{k}_threshold_pct_{e} : {v};" for k, v in (("lower", 20), ("upper", 80)) for e in ("rise", "fall"))


def fixture(tmp, positions, mode, chain=("BUF", "BUF", "BUF")):
    import test_nonport_scope_sta as F
    lib = F.LIB.replace("delay_model : table_lookup;", "delay_model : table_lookup;\n" + LIB_THRESH)
    buf = '''cell (BUFx2) { area : 1; pin (A) { direction : input; capacitance : 0.001; }
  pin (Y) { direction : output; function : "A"; timing () { related_pin : "A"; timing_sense : positive_unate;
    cell_rise (scalar) { values ("0.01"); } cell_fall (scalar) { values ("0.01"); }
    rise_transition (scalar) { values ("0.005"); } fall_transition (scalar) { values ("0.005"); } } } }
'''
    lib = lib[:lib.rindex("}")] + buf + "}\n"
    lef = F.LEF.replace("END LIBRARY\n", "") + '''MACRO BUFx2
 CLASS CORE ; ORIGIN 0 0 ; SIZE 1 BY 1 ; SITE CORE ;
 PIN A
  DIRECTION INPUT ; USE SIGNAL ;
  PORT LAYER M1 ; RECT 0.1 0.1 0.2 0.2 ; END
 END A
 PIN Y
  DIRECTION OUTPUT ; USE SIGNAL ;
  PORT LAYER M1 ; RECT 0.7 0.1 0.8 0.2 ; END
 END Y
END BUFx2
END LIBRARY
'''
    n = len(chain)
    nets = ["q0"] + [f"w{i}" for i in range(n)]
    v = "module top(input CK, DIN, output R);\nwire " + ", ".join(nets) + ";\n"
    v += "DFF u_src(.CK(CK), .D(DIN), .Q(q0));\n"
    for i in range(n):
        v += f"BUFx2 b{i}(.A({nets[i]}), .Y({nets[i + 1]}));\n"
    v += f"DFF u_dst(.CK(CK), .D({nets[n]}), .Q(R));\nendmodule\n"
    for name, c in (("f.lib", lib), ("f.lef", lef), ("f.v", v)):
        (tmp / name).write_text(c)
    place = "".join(f"[[ord::get_db_block] findInst {n}] setLocation [expr {{{int(x * 1000)}}}] [expr {{{int(y * 1000)}}}]\n" for n, (x, y) in positions.items())
    return f"""read_lef {tmp}/f.lef
read_liberty {tmp}/f.lib
read_verilog {tmp}/f.v
link_design top
{place}set ::env(REPORTS_DIR) {tmp}
set ::env(OT_PLACE_WIRE_RATIO) {mode}
catch {{source {TCL}}} msg
puts "RESULT $msg"
exit
"""


class Sta(unittest.TestCase):
    def run_fix(self, positions, mode):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cmd = openroad_cmd(tmp)
            if not cmd:
                self.skipTest("OPENROAD_BIN or the pinned ORFS image required")
            (tmp / "t.tcl").write_text(fixture(tmp, positions, mode))
            p = subprocess.run(cmd + ["-no_init", "-exit", str(tmp / "t.tcl")], capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            tsv = (tmp / "place_wire_ratio.tsv").read_text() if (tmp / "place_wire_ratio.tsv").exists() else ""
            return p.stdout, tsv

    DETOUR = {"u_src": (0, 0), "b0": (0, 600), "b1": (0, 0), "b2": (0, 600), "u_dst": (50, 0)}     # built ~2,400 um, direct 50 um
    STRAIGHT = {"u_src": (0, 0), "b0": (150, 0), "b1": (300, 0), "b2": (450, 0), "u_dst": (600, 0)}  # built 600 um, direct 600 um

    def test_detour_is_reported_and_report_mode_does_not_stop(self):
        out, tsv = self.run_fix(self.DETOUR, "report")
        self.assertIn("OT_PLACE_WIRE_RATIO mode report paths 1 violations 1", out)
        self.assertIn("u_src/Q->u_dst/D", tsv)
        self.assertNotIn("PLACE-WIRE-RATIO:", out.split("RESULT", 1)[1])

    def test_fail_mode_stops_on_the_detour_only(self):
        out, _ = self.run_fix(self.DETOUR, "fail")
        self.assertIn("RESULT PLACE-WIRE-RATIO: 1 zero-logic", out)
        out, _ = self.run_fix(self.STRAIGHT, "fail")
        self.assertIn("violations 0", out)
        self.assertNotIn("RESULT PLACE-WIRE-RATIO", out)

    def test_off(self):
        out, tsv = self.run_fix(self.DETOUR, "0")
        self.assertIn("PLACE-WIRE-RATIO off", out)
        self.assertEqual(tsv, "")


if __name__ == "__main__":
    unittest.main()
