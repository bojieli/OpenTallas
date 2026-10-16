#!/usr/bin/env python3
"""Unit tests: child_lint (a-h), abstract_pin_stub pocket closing, macro_grid_lint (mock-OpenDB placement), hier_submit (view discovery + mode)."""
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
    def run_lint(self, text, libs=None, contract=None, slot=None, skip=None, cap=None):
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
            return child_lint.lint(str(p), td if libs is not None else None, str(cp) if cp else None, slot, skip, cap)

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

    def test_face_pin_same_layer_stub_obs_fails(self):
        # ot_qkvd_sbuf (73e17f447): the pin's own M5 route stub exported as OBS overlapping the pin -> no access point
        r = self.run_lint(lef(obs=[("M5", 5.006, 0.05, 5.018, 0.6)]))
        self.assertIn("f", self.checks(r))
        self.assertEqual(r["info"]["face"]["blocked_same"], 1)
        self.assertIn("abstract_pin_stub.py", " ".join(r["fails"]))

    def test_face_pin_same_layer_edge_touch_is_fine(self):
        # same-layer OBS that only abuts the pin edge (x 5.024) or its top (y 0.192) is not a block
        r = self.run_lint(lef(obs=[("M5", 5.024, 0.0, 5.3, 0.5), ("M5", 4.9, 0.192, 5.1, 0.6)]))
        self.assertEqual(r["info"]["face"]["blocked_same"], 0)
        self.assertEqual(r["verdict"], "PASS", r["fails"])

    def test_face_pin_same_layer_band_over_many_pins_warns(self):
        # one same-layer OBS rect across two pins' inner ends = exporter edge-band decomposition: WARN, not FAIL
        r = self.run_lint(lef(sig=(("a", "M5", 5.0, 0.0), ("b", "M5", 7.0, 0.0)), obs=[("M5", 4.0, 0.1, 9.0, 0.4)]))
        self.assertEqual(r["info"]["face"]["blocked_same"], 0)
        self.assertEqual(r["info"]["face"]["band_same"], 2)
        self.assertEqual(r["verdict"], "PASS", r["fails"])
        self.assertTrue(any("several pins" in w for w in r["warns"]))

    def test_band_carve_removes_band_obs_over_face_pins(self):
        # ROOT 2026-10-15 (hbm_ckgen_rel-r1): abstract_pin_stub carves the band rect around the pins it covers; the rest
        # of the band stays OBS and no face pin keeps a same-layer OBS over it
        import abstract_pin_stub as APS
        text = lef(sig=(("a", "M5", 5.0, 0.0), ("b", "M5", 7.0, 0.0)), obs=[("M5", 4.0, 0.1, 9.0, 0.4)])
        out, _ = APS.process(text.replace("  END\nEND tile", "  END\nEND tile"))
        r = self.run_lint(out)
        self.assertEqual(r["info"]["face"]["band_same"], 0)
        self.assertEqual(r["info"]["face"]["blocked_same"], 0)
        left = APS.obs_rects(APS.split_lef(out)[1])["M5"]
        self.assertAlmostEqual(sum((c - a) * (d - b) for a, b, c, d in left), 5.0 * 0.3 - 2 * 0.024 * 0.092, places=6)

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

    # 2026-10-12 layer contract: tiles cap signals AND PG at M5 (strap M6); closed legacy views lint at their own view_cap
    def test_cap_m5_clean_and_strap_m6(self):
        r = self.run_lint(lef(pg="M5", sig=(("a", "M4", 0.0, 5.0),)), cap="M5")
        self.assertEqual(r["verdict"], "PASS", r["fails"])
        self.assertEqual((r["info"]["cap"], r["info"]["strap_layer"]), ("M5", "M6"))
        r = self.run_lint(lef(pg="M5", obs=[("M6", 8, 2, 9, 3)]), cap="M5")
        self.assertIn("c", self.checks(r))

    def test_cap_m5_signal_pin_above_cap_fails(self):
        r = self.run_lint(lef(pg="M5", sig=(("a", "M6", 0.0, 5.0),)), cap="M5")
        self.assertIn("c", self.checks(r))

    def test_slot_view_cap_keeps_legacy_view_valid(self):
        slot = {"name": "u_t", "cell": "tile", "outline": {"w": 20.0, "h": 10.0}, "pg_layer": "M5", "strap_layer": "M6",
                "signal_max_layer": "M5", "layer_cap": "M5", "view_cap": "M7",
                "pins": [{"name": "a", "face": "S", "layer": "M5"}]}
        c = {"die": "d", "version": 3, "slots": [slot]}
        r = self.run_lint(lef(pg="M7"), contract=c, slot="u_t")          # legacy M7 view, clean at its own cap
        self.assertEqual(r["verdict"], "PASS", r["fails"])
        self.assertEqual((r["info"]["cap"], r["info"]["strap_layer"]), ("M7", "M8"))
        r = self.run_lint(lef(pg="M7", obs=[("M8", 1, 1, 2, 2)]), contract=c, slot="u_t")   # breaks even its own cap
        self.assertIn("c", self.checks(r))
        r = self.run_lint(lef(pg="M5"), contract=c, slot="u_t")          # a new M5 route
        self.assertEqual(r["verdict"], "PASS", r["fails"])
        self.assertEqual(r["info"]["cap"], "M5")
        c2 = {"die": "d", "version": 3, "slots": [dict(slot, view_cap=None)]}
        r = self.run_lint(lef(pg="M7"), contract=c2, slot="u_t")         # no recorded view cap: M7 view fails the M5 slot
        self.assertTrue({"c", "e"} <= self.checks(r), r["fails"])


class ThinTileRowSpan(unittest.TestCase):
    """(b) on a tile whose outline is off the 2.16-um row/PG lattice (S81 fill dsfd_hstnh_112, 18.576 x 17.256, collect
    crashed 10-15): rows and M5 stripes 2.151..14.859/14.873 stop 0.237 um short of the 2.16-um top inset.  A stripe
    crossing every cell row is a full PG connection; a stripe missing a row, or a shrunken core, still FAILs."""
    W, H = 18.576, 17.256

    def text(self, y0=2.151, y1=14.873, rows=(2.16, 2.151, 16.416, 14.859)):
        out = [f"VERSION 5.8 ;\nMACRO tile\n  CLASS BLOCK ;\n  SIZE {self.W} BY {self.H} ;"]
        for i, n in enumerate(("VDD", "VSS")):
            rects = "\n".join(f"        RECT {2.592 + 2.7 * k + 1.35 * i:.3f} {y0} {2.712 + 2.7 * k + 1.35 * i:.3f} {y1} ;"
                              for k in range(5))
            out.append(f"  PIN {n}\n    USE {'POWER' if n == 'VDD' else 'GROUND'} ;\n    PORT\n      LAYER M5 ;\n{rects}\n"
                       f"    END\n  END {n}")
        out.append("  PIN a\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M4 ;\n        RECT 0 5.952 0.084 5.976 ;"
                   "\n    END\n  END a")
        out.append("  OBS\n    LAYER M1 ;\n      RECT %g %g %g %g ;\n  END" % rows)
        out.append("END tile\nEND LIBRARY\n")
        return "\n".join(out)

    def lint(self, text):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tile.lef"
            p.write_text(text)
            return child_lint.lint(str(p), skip={"g"})

    def test_off_lattice_rows_fully_crossed_pass(self):
        r = self.lint(self.text())
        self.assertNotIn("b", {f[1] for f in r["fails"]}, r["fails"])
        self.assertEqual(r["info"]["pg"]["nets"]["VDD"]["stripes"], 5)

    def test_stripe_missing_top_row_fails(self):
        r = self.lint(self.text(y1=14.5))
        self.assertIn("b", {f[1] for f in r["fails"]})

    def test_shrunken_core_fails(self):
        # rows end 3 um below the top inset: stripes cover them, but the core is not the tile -> not full-length
        r = self.lint(self.text(y1=12.1, rows=(2.16, 2.151, 16.416, 12.0)))
        self.assertIn("b", {f[1] for f in r["fails"]})

    def test_no_m1_rows_keeps_old_rule(self):
        r = self.lint(self.text().replace("    LAYER M1 ;\n      RECT 2.16 2.151 16.416 14.859 ;\n", ""))
        self.assertIn("b", {f[1] for f in r["fails"]})


class Pockets(unittest.TestCase):
    """abstract_pin_stub pocket closing + child_lint (h)"""
    # two M5 blocks 0.5 um apart (pocket), M5 pin 'p' on the west face inside a 0.3-um slot, PG on M7 (not an obstacle)
    OBS = [("M5", 6, 2, 8, 6), ("M5", 8.5, 2, 12, 6), ("M5", 0.3, 4.0, 3, 4.4), ("M5", 0.3, 4.7, 3, 5.2)]

    def text(self, obs=None, sig=(("a", "M4", 5.0, 0.0), ("p", "M5", 0.0, 4.5))):
        return lef(obs=self.OBS if obs is None else obs, sig=sig)

    def close(self, text):
        import abstract_pin_stub as APS
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.lef"
            p.write_text(text)
            self.assertEqual(APS.main([str(p), str(p)]), 0)
            return p.read_text()

    def lint_text(self, text, **kw):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tile.lef"
            p.write_text(text)
            return child_lint.lint(str(p), **kw)

    def m5(self, text):
        import abstract_pin_stub as APS
        return APS.obs_rects(APS.split_lef(text)[1])["M5"]

    def test_pocket_closed_boundary_and_pin_kept(self):
        import abstract_pin_stub as APS
        before = APS.find_pockets(self.text())
        self.assertEqual(before["layer"], "M5")
        self.assertIn((8.0, 2.0, 8.5, 6.0), before["rects"])
        out = self.close(self.text())
        self.assertIn("# OT_OBS_CLOSED layer=M5 d_um=1.536 added=", out)
        self.assertIn((8.0, 2.0, 8.5, 6.0), self.m5(out))
        self.assertEqual(APS.find_pockets(out)["rects"], [])
        added = [r for r in self.m5(out) if r not in [o[1:] for o in self.OBS]]
        # boundary gaps stay open: nothing left of the first obstacle column (x < 0.3) or right of the last (x > 12)
        self.assertTrue(all(r[0] >= 0.3 and r[2] <= 12 for r in added), added)
        # pin p (0..0.192, 4.5..4.524): no fill within one M5 pitch (0.048) of it, although its slot is 0.3 um wide
        keep = (0 - 0.048, 4.5 - 0.048, 0.192 + 0.048, 4.524 + 0.048)
        self.assertFalse([r for r in added if APS._ov(r, keep)])
        # the 0.3-um slot between the two west bars IS closed away from the pin
        self.assertTrue(any(r[1] >= 4.4 - 1e-9 and r[3] <= 4.7 + 1e-9 and r[2] > 2 for r in added), added)
        self.assertEqual(self.close(out), out)  # idempotent

    def test_wide_gap_and_single_obstacle_untouched(self):
        import abstract_pin_stub as APS
        self.assertEqual(APS.find_pockets(self.text(obs=[("M5", 2, 2, 4, 6), ("M5", 8, 2, 10, 6)]))["rects"], [])
        self.assertEqual(APS.find_pockets(self.text(obs=[("M5", 2, 2, 4, 6)]))["rects"], [])

    def test_pg_pin_rect_is_an_obstacle(self):
        import abstract_pin_stub as APS
        # PG stripes on M5 (y 1..1.3, 1.5..1.8, ...): an M5 OBS 0.4 um above the VSS stripe at 1.5..1.8 closes onto it
        r = APS.find_pockets(lef(pg="M5", obs=[("M5", 6, 2.2, 8, 2.6)], sig=(("a", "M4", 5.0, 0.0),)))
        self.assertIn((6.0, 1.8, 8.0, 2.2), r["rects"])

    def test_disabled_writes_no_marker(self):
        import os
        os.environ["OT_OBS_CLOSE"] = "0"
        try:
            out = self.close(self.text())
        finally:
            del os.environ["OT_OBS_CLOSE"]
        self.assertNotIn("OT_OBS_CLOSED", out)
        self.assertEqual(sorted(self.m5(out)), sorted(o[1:] for o in self.OBS))

    def test_lint_h_policy(self):
        r = self.lint_text(self.text())
        self.assertEqual(r["verdict"], "PASS", r["fails"])
        self.assertTrue(any(w.startswith("(h)") and "--strict-pockets" in w for w in r["warns"]), r["warns"])
        r = self.lint_text(self.text(), strict_pockets=True)
        self.assertEqual({f[1] for f in r["fails"]}, {"h"})
        self.assertNotIn("h", {f[1] for f in self.lint_text(self.text(), strict_pockets=True, skip={"h"})["fails"]})
        out = self.close(self.text())
        r = self.lint_text(out, strict_pockets=True)
        self.assertEqual(r["verdict"], "PASS", r["fails"])
        self.assertFalse([w for w in r["warns"] if w.startswith("(h)")])
        self.assertEqual(r["info"]["pockets"]["count"], 0)
        # a marked LEF that still has a pocket (edited after the export) FAILs without --strict-pockets
        bad = out.replace("  OBS\n", "  OBS\n    LAYER M5 ;\n      RECT 14 2 15 6 ;\n      RECT 15.4 2 16 6 ;\n", 1)
        self.assertEqual({f[1] for f in self.lint_text(bad)["fails"]}, {"h"})

    def test_lint_h_fails_loudly_without_the_detector(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "child_lint.py").write_text((HERE / "child_lint.py").read_text())
            p = Path(td) / "tile.lef"
            p.write_text(self.text())
            import subprocess
            for stale in (None, "import sys\nsrc, dst = sys.argv[1], sys.argv[2]\nopen(dst, 'w').write('clobbered')\n"):
                if stale:
                    (Path(td) / "abstract_pin_stub.py").write_text(stale)
                cp = subprocess.run([sys.executable, str(Path(td) / "child_lint.py"), str(p), "--skip", "g"],
                                    capture_output=True, text=True, cwd=td)
                self.assertEqual(cp.returncode, 1, cp.stdout + cp.stderr)
                self.assertIn("FAIL (h) pockets: detector unavailable", cp.stdout)
                self.assertEqual(sorted(x.name for x in Path(td).iterdir() if x.suffix != ".pyc" and x.is_file()),
                                 sorted(["child_lint.py", "tile.lef"] + (["abstract_pin_stub.py"] if stale else [])))

    def test_real_hcp_lanes_pocket(self):
        """hc_tile_xl-c4-550082537-hs: M6 pocket x 12.947..13.139, y 23.84..25.616 (the view as exported at 6a28f232b)"""
        import abstract_pin_stub as APS
        import subprocess
        root = HERE.parents[1]
        rel = "physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes/ot_hdc_v41x_hcp_lanes.lef"
        cp = subprocess.run(["git", "-C", str(root), "show", f"f43c2d3cc:{rel}"], capture_output=True, text=True)
        if cp.returncode != 0 or "MACRO" not in cp.stdout:
            self.skipTest("pre-fix hcp_lanes view not reachable in this checkout")
        P = (12.947, 23.84, 13.139, 25.616)
        cov = lambda rs: any(a <= P[0] + 1e-9 and b <= P[1] + 1e-9 and c >= P[2] - 1e-9 and e >= P[3] - 1e-9 for a, b, c, e in rs)
        before = APS.find_pockets(cp.stdout)
        self.assertEqual((before["layer"], before["d_um"]), ("M6", 2.048))
        self.assertTrue(cov(before["rects"]), "reported pocket not detected")
        self.assertFalse(cov(APS.obs_rects(APS.split_lef(cp.stdout)[1])["M6"]))
        out = self.close(cp.stdout)
        self.assertTrue(cov(APS.obs_rects(APS.split_lef(out)[1])["M6"]), "reported pocket not covered")
        self.assertEqual(APS.find_pockets(out)["rects"], [])
        r = self.lint_text(out, strict_pockets=True, skip={"g"})
        self.assertEqual(r["verdict"], "PASS", r["fails"])


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

    def test_hard_tile_via_sourced_cfg(self):
        """route_master.sh CFG=$1 + source cfg/$CFG.env (EXTRA=(... MACRO_PLACEMENT_TCL=...)): a hard tile on a 1.08 um
        grid is refused, on the 8.64 um grid it passes (qkd_d2d_h-305021c34 vs 04612c41b)"""
        tile = lef(name="ot_tile_t", W=30.0, H=20.0, sig=(("d", "M5", 1.2, 0.0),))     # M5 x centre 1.212 = 0.012 + 0.048 * 25
        tcl = """set b [ord::get_db_block]; set c [$b getCoreArea]
set k 0
foreach m [$b getInsts] { $m setOrient R0
  $m setLocation [expr {round(%s * round(([$c xMin]/1000.0 + 40.0 + $k*50.0)/%s) * 1000)}] 21600; incr k }
"""
        spec = {"name": "j", "source": {"commit": "c"}, "stages": {"route": {
            "cmd": "HM=0.01 bash physical/x/jobs/route_master.sh tq {LABEL} {RUN}/routes"}}}
        for grid, want in (("1.08", "REFUSE"), ("8.64", "PASS")):
            g = FakeGit({"physical/x/jobs/route_master.sh": "CFG=$1; NAME=$2\nsource physical/x/cfg/$CFG.env\n"
                                                           "run --die-area 0 0 $FW $FH --core-area 2.16 2.16 x y\n",
                         "physical/x/cfg/tq.env": "FW=200\nFH=200\nEXTRA=(--macro-view ot_tile_t=physical/v/ot_tile_t "
                                                  "--orfs-var MACRO_PLACEMENT_TCL=/src/physical/x/p.tcl)\n",
                         "physical/v/ot_tile_t/ot_tile_t.lef": tile, "physical/x/p.tcl": tcl % (grid, grid)})
            r = macro_grid_lint.check(spec, g)
            self.assertEqual(r["verdict"], want, r["message"])

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
