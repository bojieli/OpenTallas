#!/usr/bin/env python3
"""Unit tests of the TILE-FLOW 2026-10-23 tile planning: content outline, macro array, face fence wiring, audit."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import tile_plan as TP  # noqa: E402
import ref_tile as RT  # noqa: E402


def tm_box(name, w_um, h_um, faces, n=100, power_full_width=True):
    """a synthetic parse_lef macro: n signal pins on each listed face, PG stripes spanning the width"""
    W, H = round(w_um * 1000), round(h_um * 1000)
    pins = []
    for f in faces:
        for i in range(n):
            if f in "WE":
                y = 500 + i * (H - 1000) // max(1, n)
                x0 = 0 if f == "W" else W - 24
                pins.append({"name": f"{f}{i}", "use": "SIGNAL", "rects": [("M4", (x0, y, x0 + 24, y + 24))]})
            else:
                x = 500 + i * (W - 1000) // max(1, n)
                y0 = 0 if f == "S" else H - 24
                pins.append({"name": f"{f}{i}", "use": "SIGNAL", "rects": [("M4", (x, y0, x + 24, y0 + 24))]})
    if power_full_width:
        pins.append({"name": "VDD", "use": "POWER", "rects": [("M4", (300, 384, W - 300, 480))]})
    return {"name": name, "W": W, "H": H, "pins": pins, "obs": [], "class": "BLOCK", "symmetry": ""}


def macros(tm, k):
    return [{"w": tm["W"] / 1000, "h": tm["H"] / 1000, "tm": tm, "key": i} for i in range(k)]


class Outline(unittest.TestCase):
    def test_area_bound_logic_tile(self):
        # 40k um2 of std cells, 600 pins on N/S: content-sized, near-square, fill near the 0.65 target
        r = TP.content_outline(40000, [], {"N": 300, "S": 300, "E": 0, "W": 0})
        self.assertEqual(r["bound"], "area")
        core = (r["w"] - 4.32) * (r["h"] - 4.32)
        self.assertLess(core, 40000 / 0.60 + 600 * TP.FF_AREA_UM2 / TP.BAND_FILL + 3000)
        self.assertGreater(r["fill"], 0.55)
        self.assertLessEqual(max(r["w"], r["h"]) / min(r["w"], r["h"]), TP.ASPECT_MAX + 1e-9)

    def test_pin_bound_tile_reports_pins(self):
        # 6000 pins on W / E, little logic: H from 3 pins/um, aspect capped at 2
        r = TP.content_outline(5000, [], {"N": 0, "S": 0, "E": 3000, "W": 3000})
        self.assertEqual(r["bound"], "pins")
        self.assertGreaterEqual(r["h"] - 4.32, 3000 / TP.PIN_DENSITY - 1e-6)
        self.assertLessEqual(max(r["pin_density"].values()), TP.PIN_DENSITY + 1e-6)
        self.assertLessEqual(r["h"] / r["w"], TP.ASPECT_MAX + 1e-6)

    def test_aspect_follows_pin_demand(self):
        r = TP.content_outline(200000, [], {"N": 1500, "S": 1500, "E": 200, "W": 200})
        self.assertGreater(r["w"], r["h"])            # long faces where the pins are

    def test_util_range_enforced(self):
        with self.assertRaises(ValueError):
            TP.content_outline(1000, [], {}, util=0.5)

    def test_slot_check_requests_rederivation(self):
        r = TP.content_outline(200000, [], {"N": 10}, slot=(200.0, 200.0))
        self.assertFalse(r["slot"]["fits"])
        self.assertIn("parent slot must be re-derived", r["slot"]["request"])
        r = TP.content_outline(2000, [], {"N": 10}, slot=(400.0, 400.0))
        self.assertTrue(r["slot"]["fits"])

    def test_outline_flag(self):
        comp = TP.content_outline(20000, [], {"N": 100, "S": 100})
        big = (comp["w"] * 2, comp["h"] * 2)
        sev, msg = TP.outline_flag(big, comp, {})
        self.assertEqual(sev, "FAIL")
        self.assertIn("content outline", msg)
        self.assertEqual(TP.outline_flag(big, comp, {"outline_reason": "die slot hole"})[0], "INFO")
        self.assertIsNone(TP.outline_flag((comp["w"], comp["h"]), comp, {}))

    def test_fence_depth(self):
        self.assertEqual(TP.fence_depth_um(0, 100), 0.0)
        self.assertEqual(TP.fence_depth_um(10, 500), TP.BAND_MIN_UM)
        self.assertEqual(TP.fence_depth_um(100000, 100), TP.BAND_MAX_UM)
        d = TP.fence_depth_um(3000, 300)              # 10 regs/um -> 5.83 um -> whole rows
        self.assertAlmostEqual(d / TP.ROW_UM, round(d / TP.ROW_UM), places=6)


class MacroPlan(unittest.TestCase):
    def test_dual_face_arrays_columns_with_channels(self):
        tm = tm_box("sram_we", 170.0, 30.0, "WE")
        r = TP.plan_macros(1200, 600, macros(tm, 8), {"N": 0, "S": 400, "E": 0, "W": 0})
        self.assertTrue(r["ok"])
        self.assertEqual(r["edge"], "N")              # the pin-free face carries the array
        cols = {}
        for p in r["placed"]:
            cols.setdefault(p["col"], []).append(p)
        for c in cols.values():                       # N-S abutted: pitch = height + 0.024
            ys = sorted(p["y"] for p in c)
            for a, b in zip(ys, ys[1:]):
                self.assertAlmostEqual(b - a, 30.0 + TP.ABUT_PITCH_UM, places=3)
        for p in r["placed"]:                         # W and E pins: both faces get a channel >= 20 um
            self.assertEqual(p["pin_faces"], ["E", "W"])
        self.assertTrue(all(g >= TP.CHANNEL_MIN_UM for g in r["gaps"]))
        self.assertGreaterEqual(r["lead"], TP.CHANNEL_MIN_UM)

    def test_single_face_arrays_face_each_other(self):
        tm = tm_box("sram_w", 100.0, 20.0, "W")
        r = TP.plan_macros(800, 800, macros(tm, 4), {"S": 100}, rows=2)
        faces = sorted({(p["col"], p["pin_faces"][0]) for p in r["placed"]})
        self.assertEqual(faces, [(0, "E"), (1, "W")])  # col 0 pins E, col 1 pins W: one shared logic channel
        o = {p["col"]: p["orient"] for p in r["placed"]}
        self.assertEqual((o[0], o[1]), ("MY", "R0"))

    def test_ns_pinned_arrays_transposed(self):
        tm = tm_box("sram_s", 30.0, 170.0, "S")
        r = TP.plan_macros(600, 1200, macros(tm, 4), {"E": 200})
        self.assertEqual(r["axis"], "NS")
        self.assertIn(r["edge"], ("W", "E"))
        self.assertTrue(all(p["pin_faces"][0] in ("N", "S") for p in r["placed"]))

    def test_content_outline_grows_for_the_array(self):
        tm = tm_box("sram_we", 170.0, 30.0, "WE", n=200)
        r = TP.content_outline(2000, macros(tm, 10), {"S": 100})
        self.assertTrue(r["macro_plan"]["ok"])
        self.assertEqual(r["bound"], "macros")

    def test_orient_for(self):
        self.assertEqual(TP.orient_for("W", "E"), "MY")
        self.assertEqual(TP.orient_for("S", "N"), "MX")
        self.assertEqual(TP.face_after("R180", "W"), "E")


class NonAnsiPorts(unittest.TestCase):
    def test_non_ansi_header(self):
        v = "module top (a, b, c);\n  input [7:0] a;\n  output b;\n  output [0:3] c, ;\nendmodule\n"
        self.assertIsNone(TP.non_ansi_widths(v, "top"))         # malformed list: no estimate
        v = "module top (a, b, c);\n  input [7:0] a;\n  output b;\n  output [0:3] c;\nendmodule\n"
        self.assertEqual(TP.non_ansi_widths(v, "top"), {"a": 8, "b": 1, "c": 4})

    def test_face_demand_skips_clocks(self):
        s = {"clock_port": "clk", "pins": {"W": ["clk", "a"], "E": ["b"]}}
        d, exact = TP.face_demand(s, {"clk": 1, "a": 8, "b": 3})
        self.assertEqual((d["W"], d["E"], exact), (8, 3, True))
        d, exact = TP.face_demand(s, None)
        self.assertFalse(exact)


EXN = "nhb_pbst_ref"


def spec_file(root, **kw):
    s = json.loads((HERE / "examples" / f"{EXN}.json").read_text())
    s.update(kw)
    p = Path(root) / f"{s['name']}.json"
    p.write_text(json.dumps(s))
    return str(p)


class Recipe5(unittest.TestCase):
    def gen(self, root, **kw):
        kw.setdefault("route", {"pd": 0.5})
        r = RT.gen(spec_file(root, **kw), commit="c" * 40, out_root=Path(root))
        d = Path(root) / r["kit"]
        return r, {f.name: f.read_text() for f in d.iterdir()}

    def test_new_tile_takes_tile_plan_and_fence(self):
        with tempfile.TemporaryDirectory() as a:
            r, k = self.gen(a, name="tp5_a", std_area_um2=3000.0, outline=None)
            self.assertIn(f"RECIPE={RT.RECIPE_LATEST}", k["kit.env"])
            self.assertEqual(RT.RECIPE_LATEST, 5)
            self.assertIn("source /src/physical/common_flow/pin_reg_face_fence.tcl", k["pre_gpl.tcl"])
            gpl = [x for x in k["pre_gpl.tcl"].splitlines() if x.startswith("source ")]
            self.assertLess(gpl.index("source /src/physical/qwen_die_masters/io_flop_at_pins.tcl"),
                            gpl.index("source /src/physical/common_flow/pin_reg_face_fence.tcl"))
            self.assertIn("OT_FENCE_STRICT=1", k["kit.env"])
            self.assertIn("physical/common_flow/pin_reg_face_fence.tcl", json.loads(k["floorplan.json"])["referenced"])
            sp = json.loads(k["spec.json"])
            self.assertEqual(sp["pin_regs"]["enable"], False)        # registers from the RTL
            self.assertFalse(any(x.startswith("_tp") for x in sp))
            fp = json.loads(k["floorplan.json"])
            self.assertIn("tile_plan", fp)
            self.assertIn("content:", fp["why"])
            self.assertTrue((RT.ROOT / "physical/common_flow/pin_reg_face_fence.tcl").is_file())

    def test_wrapper_refused_and_unregistered_ok_exported(self):
        with tempfile.TemporaryDirectory() as a:
            with self.assertRaises(RT.SpecError):
                self.gen(a, name="tp5_w", std_area_um2=3000.0, outline=None, pin_regs={"enable": True})
            with self.assertRaises(RT.SpecError):
                self.gen(a, name="tp5_x", std_area_um2=3000.0, outline=None, unregistered_ok={"sr": ""})
            r, k = self.gen(a, name="tp5_u", std_area_um2=3000.0, outline=None,
                            unregistered_ok={"sr": "status strap read by the die once at boot"})
            self.assertIn("OT_FENCE_UNREG_OK=sr", k["kit.env"])

    def test_explicit_big_outline_fails_without_reason(self):
        with tempfile.TemporaryDirectory() as a:
            r, _ = self.gen(a, name="tp5_b", std_area_um2=1500.0, outline={"w": 500.0, "h": 500.0})
            fails = [f for f in r["findings"] if f[1] == "outline_ratio"]
            self.assertEqual(fails[0][0], "FAIL")
            r, _ = self.gen(a, name="tp5_c", std_area_um2=1500.0, outline={"w": 500.0, "h": 500.0},
                            outline_reason="die slot hole: pins abut the neighbours")
            self.assertEqual([f[0] for f in r["findings"] if f[1] == "outline_ratio"], ["INFO"])

    def test_tile_plan_off_keeps_recipe_4_behaviour(self):
        with tempfile.TemporaryDirectory() as a:
            _, k = self.gen(a, name="tp5_off", tile_plan=False)
            self.assertNotIn("pin_reg_face_fence", k["kit.env"] + k.get("pre_gpl.tcl", ""))


if __name__ == "__main__":
    unittest.main()
