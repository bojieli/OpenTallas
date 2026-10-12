#!/usr/bin/env python3
"""Unit tests: child_lint (a-g), macro_grid_lint (mock-OpenDB placement), hier_submit (view discovery + mode)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import child_lint  # noqa: E402
import hier_submit  # noqa: E402
import macro_grid_lint  # noqa: E402


def lef(name="tile", W=20.0, H=10.0, pg="M7", obs=(), sig=(("a", "M5", 5.0, 0.0),), stripes=3, extra=""):
    """synthetic hard-child LEF: horizontal PG stripes on pg (full width), signal pins (name, layer, x, y) 0.024 x 0.192"""
    out = [f"VERSION 5.8 ;\nMACRO {name}\n  CLASS BLOCK ;\n  SIZE {W} BY {H} ;"]
    for i, n in enumerate(("VDD", "VSS")):
        rects = "\n".join(f"        RECT 0 {1 + 3.5 * k + 0.5 * i:.3f} {W} {1.3 + 3.5 * k + 0.5 * i:.3f} ;" for k in range(stripes))
        out.append(f"  PIN {n}\n    USE {'POWER' if n == 'VDD' else 'GROUND'} ;\n    PORT\n      LAYER {pg} ;\n{rects}\n    END\n  END {n}")
    for n, ly, x, y in sig:
        x1, y1 = (x + 0.024, y + 0.192) if y in (0.0, H - 0.192) else (x + 0.192, y + 0.024)
        out.append(f"  PIN {n}\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER {ly} ;\n        RECT {x} {y} {x1} {y1} ;\n    END\n  END {n}")
    if obs:
        out.append("  OBS\n" + "\n".join(f"    LAYER {ly} ;\n      RECT {a} {b} {c} {d} ;" for ly, a, b, c, d in obs) + "\n  END")
    out.append(extra + f"END {name}\nEND LIBRARY\n")
    return "\n".join(out)


TT_LIB = '''library(x) { time_unit : "1ps"; cell ("tile") { pin("clk") { direction : input; clock : true;
 timing() { timing_type : min_clock_tree_path; cell_rise(scalar) { values("140.0"); } }
 timing() { timing_type : max_clock_tree_path; cell_rise(scalar) { values("150.0"); } } } } }'''


class ChildLint(unittest.TestCase):
    def run_lint(self, text, libs=None, contract=None, slot=None, skip=None):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tile.lef"
            p.write_text(text)
            if libs:
                for c, body in libs.items():
                    (Path(td) / f"tile_{c}.lib").write_text(body)
            cp = None
            if contract:
                cp = Path(td) / "die.json"
                cp.write_text(json.dumps(contract))
            return child_lint.lint(str(p), td if libs is not None else None, str(cp) if cp else None, slot, skip)

    def checks(self, r):
        return {f[1] for f in r["fails"]}

    def test_clean_passes(self):
        r = self.run_lint(lef(obs=[("M1", 0, 0, 20, 10), ("M5", 8, 2, 9, 3)]))
        self.assertEqual(r["verdict"], "PASS", r["fails"])
        self.assertEqual(r["info"]["pg"]["nets"]["VDD"]["stripes"], 3)

    def test_bloat_fails(self):
        r = self.run_lint(lef(pg="M6", obs=[("M6", 0, 0, 20, 10)]))
        self.assertIn("a", self.checks(r))

    def test_full_m1_obs_below_pg_is_fine(self):
        r = self.run_lint(lef(obs=[("M1", 0, 0, 20, 10)]))
        self.assertNotIn("a", self.checks(r))

    def test_strap_layer_obs_fails(self):
        r = self.run_lint(lef(pg="M6", obs=[("M7", 1, 1, 2, 2)]))
        self.assertIn("c", self.checks(r))
        self.assertEqual(r["info"]["strap_layer"], "M7")

    def test_pg_not_full_length(self):
        r = self.run_lint(lef(stripes=1))
        self.assertIn("b", self.checks(r))

    def test_face_pin_blocked_above(self):
        r = self.run_lint(lef(obs=[("M6", 4.9, 0.06, 6.0, 1.8)]))
        self.assertIn("f", self.checks(r))
        self.assertEqual(r["info"]["face"]["blocked_above"], 1)
        self.assertIn("pin_access_pregrt.tcl", " ".join(r["fails"]))

    def test_libs_and_insertion(self):
        r = self.run_lint(lef(), libs={"tt": TT_LIB, "ff": ""})
        self.assertIn("d", self.checks(r))
        self.assertEqual(r["info"]["clock_insertion"]["clk"], {"max_ps": 150.0, "min_ps": 140.0})
        c = {"die": "d", "version": 1, "slots": [{"name": "u_t", "cell": "tile", "outline": {"w": 20.0, "h": 10.0},
                                                  "pg_layer": "M7", "target_insertion_ps": 400,
                                                  "pins": [{"name": "a", "face": "S", "layer": "M5"}]}]}
        r = self.run_lint(lef(), libs={"tt": TT_LIB, "ff": "", "ss": ""}, contract=c, slot="u_t")
        self.assertEqual(r["verdict"], "PASS", r["fails"])
        self.assertTrue(any(w.startswith("(g)") and "400" in w for w in r["warns"]))

    def test_contract_mismatch(self):
        c = {"die": "d", "version": 2, "slots": [{"name": "u_t", "outline": {"w": 20.0, "h": 12.0}, "pg_layer": "M6",
                                                  "pins": [{"name": "a", "face": "N", "layer": "M5"},
                                                           {"name": "b", "face": "S", "layer": "M5"}]}]}
        r = self.run_lint(lef(), contract=c, slot="u_t")
        e = [f for f in r["fails"] if f.startswith("(e)")]
        self.assertTrue(any("outline" in f for f in e) and any("PG layer" in f for f in e))
        self.assertTrue(any("missing" in f for f in e) and any("face/layer" in f for f in e))


class FakeGit:
    def __init__(self, files):
        self.files = files

    def show(self, commit, path):
        return self.files.get(path)

    def exists(self, commit, path):
        return path in self.files

    def ls(self, commit, d):
        return sorted({p[len(d) + 1:].split("/")[0] for p in self.files if p.startswith(d + "/")})


SRAM = lef(name="ot_sram_t", W=10.0, H=10.0, pg="M4", sig=(("d", "M4", 0.0, 0.96),), stripes=2)  # pin centre y 0.972 = 0.012 + 0.048 * 20


def place_spec(tcl_name):
    return {"name": "j", "source": {"commit": "c"}, "stages": {"route": {
        "cmd": f"bash physical/x/route.sh --die-area 0 0 100 100 --macro-view ot_sram_t=physical/m/ot_sram_t "
               f"--orfs-var MACRO_PLACEMENT_TCL=/src/physical/x/{tcl_name}"}}}


PLACE = """set b [ord::get_db_block]
foreach i [$b getInsts] { if {[[$i getMaster] getName] eq "ot_sram_t"} { lappend m $i } }
if {[llength $m] != 2} { error "expected 2 macros, found [llength $m]" }
set y0 [expr {28.8 + %s}]
set k 0
foreach i $m { $i setOrient R0; $i setLocation [expr {round(20.0*1000)}] [expr {round(($y0 + $k*30.0)*1000)}]; incr k }
"""


class MacroGrid(unittest.TestCase):
    def git(self, extra):
        return FakeGit({"physical/x/route.sh": "echo route", "physical/m/ot_sram_t/ot_sram_t.lef": SRAM, **extra})

    def test_offgrid_refused(self):
        g = self.git({"physical/x/p.tcl": PLACE % "0.010"})          # y0 = 28.81: pin centre 29.782, off M4 track
        r = macro_grid_lint.check(place_spec("p.tcl"), g)
        self.assertEqual(r["verdict"], "REFUSE", r["message"])
        self.assertIn("ot_sram_t at (20.000, 28.810)", r["message"])

    def test_ongrid_passes(self):
        g = self.git({"physical/x/p.tcl": PLACE % "0.0"})            # y0 = 28.8: centre 29.772 = 0.012 + 0.048k
        r = macro_grid_lint.check(place_spec("p.tcl"), g)
        self.assertEqual(r["verdict"], "PASS", r["message"])

    def test_literal_place_macro(self):
        g = self.git({"physical/x/p.tcl": "place_macro -macro_name {u_a.ot_sram_t} -location {20.0 30.006} -orientation R0\n"})
        r = macro_grid_lint.check(place_spec("p.tcl"), g)
        self.assertEqual(r["verdict"], "REFUSE")

    def test_opt_out(self):
        s = place_spec("p.tcl")
        s["macro_grid_lint"] = False
        self.assertEqual(macro_grid_lint.check(s, self.git({})), {"verdict": "SKIP", "message": "macro_grid_lint opted out"})


class HierSubmit(unittest.TestCase):
    def spec(self, **kw):
        return {"name": "p", "source": {"commit": "c"}, **kw, "stages": {"route": {
            "cmd": "python3 tools/top.py --view8 {SRC}/physical/v/bad_tile --view5 physical/v/good_tile --out x"}}}

    def git(self):
        bad = lef(name="bad_tile", pg="M6", obs=[("M6", 0, 0, 20, 10)])
        good = lef(name="good_tile")
        return FakeGit({"tools/top.py": "", "physical/v/bad_tile/bad_tile.lef": bad,
                        "physical/v/good_tile/good_tile.lef": good, "physical/v/good_tile/good_tile_tt.lib": TT_LIB,
                        "physical/v/good_tile/good_tile_ff.lib": "x", "physical/v/good_tile/good_tile_ss.lib": "x"})

    def test_finds_children_and_modes(self):
        self.assertEqual(hier_submit.child_views(self.spec(), self.git()),
                         ["physical/v/bad_tile/bad_tile.lef", "physical/v/good_tile/good_tile.lef"])
        r = hier_submit.check(self.spec(), self.git(), "warn")
        self.assertEqual(r["verdict"], "WARN")
        self.assertIn("bad_tile.lef: (a) bloat", r["message"])
        self.assertEqual(r["views"]["physical/v/good_tile/good_tile.lef"]["verdict"], "PASS")
        self.assertEqual(hier_submit.check(self.spec(), self.git(), "refuse")["verdict"], "REFUSE")
        self.assertEqual(hier_submit.check(self.spec(hier_lint=False), self.git(), "refuse")["verdict"], "SKIP")


if __name__ == "__main__":
    unittest.main()
