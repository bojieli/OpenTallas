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
        # 6000 pins on W / E, little logic: H from 6 pins/um (two layers), aspect capped at 2
        r = TP.content_outline(5000, [], {"N": 0, "S": 0, "E": 3000, "W": 3000})
        self.assertEqual(TP.PIN_DENSITY, 6.0)
        self.assertEqual(r["bound"], "pins")
        self.assertGreaterEqual(r["h"] - 4.32, 3000 / TP.PIN_DENSITY - 1e-6)
        self.assertLessEqual(max(r["pin_density"].values()), TP.PIN_DENSITY + 1e-6)
        self.assertLessEqual(r["h"] / r["w"], TP.ASPECT_MAX + 1e-6)
        self.assertTrue(all(c["ok"] for c in r["pin_check"].values()))


class LogicFace(unittest.TestCase):
    def test_dual_face_banks_face_one_logic_band(self):
        # lep-like: dual-face SRAMs (clock on the W LEF face): logic_face E -> MY, array against the W keep-off
        tm = tm_box("dual", 174.0, 29.7, "WE", n=100)
        tm["pins"].append({"name": "clk", "use": "CLOCK", "rects": [("M4", (0, 1000, 24, 1024))]})
        dem = {"N": 0, "S": 700, "E": 2200, "W": 2200}
        r = TP.plan_macros(500.0, 420.0, macros(tm, 10), dem, logic_face="E")
        self.assertTrue(r["ok"], r)
        self.assertEqual({p["orient"] for p in r["placed"]}, {"MY"})
        self.assertEqual(TP.primary_face(tm), "W")
        x_max = max(p["x"] + p["w"] for p in r["placed"])
        self.assertGreater(500.0 - x_max, 200.0)                    # the free width is ONE band at the E side
        c = TP.plan_macros(500.0, 420.0, macros(tm, 10), dem)       # default: centred, R0
        self.assertEqual({p["orient"] for p in c["placed"]}, {"R0"})
        with self.assertRaises(ValueError):
            TP.plan_macros(500.0, 420.0, macros(tm, 10), dem, logic_face="N")
        # back-face pins (100 / macro on a 29.7-um macro: 464 M6 tracks x 0.45 = 209) cross over the macro on M6
        ov = {"WE": TP.over_pitch_for(TP.face_pin_layers("M6"), "WE")}
        o = TP.plan_macros(500.0, 420.0, macros(tm, 10), dem, logic_face="E", over=ov)
        self.assertEqual(o["over_macro_cols"], [0])
        self.assertEqual(o["lead"], 0.0)
        self.assertLess(o["need"][0], r["need"][0])
        # no logic_face, M6 over the macros: dual-face columns mirror in pairs, control faces share the middle channel
        pr = TP.plan_macros(500.0, 300.0, macros(tm, 8), dem, over=ov, rows=4)
        self.assertEqual([p["orient"] for p in pr["placed"] if p["col"] == 0][0], "MY")
        self.assertEqual([p["orient"] for p in pr["placed"] if p["col"] == 1][0], "R0")
        self.assertEqual((pr["lead"], pr["trail"]), (0.0, 0.0))
        # M5 cap: no horizontal layer above the M4 OBS -> the back channel stays
        o5 = TP.plan_macros(500.0, 420.0, macros(tm, 10), dem, logic_face="E",
                            over={"WE": TP.over_pitch_for(TP.face_pin_layers("M5"), "WE")})
        self.assertEqual(o5["over_macro_cols"], [])


class TiedPins(unittest.TestCase):
    def test_strip_repair_and_tied_mask(self):
        tm = tm_box("m", 100.0, 30.0, "WE", n=4)
        tm["pins"] += [{"name": f"rr_addr[{i}]", "use": "SIGNAL", "rects": [("M4", (99976, 500 + 30 * i, 100000, 524 + 30 * i))]}
                       for i in range(5)]
        tm["pins"] += [{"name": f"w_mask_in[{i}]", "use": "SIGNAL", "rects": [("M4", (99976, 800 + 30 * i, 100000, 824 + 30 * i))]}
                       for i in range(7)]
        self.assertEqual(TP.macro_pin_faces(tm)["E"], 16)
        self.assertEqual(TP.macro_pin_faces(TP.strip_pins(tm))["E"], 11)
        self.assertEqual(TP.macro_pin_faces(TP.strip_pins(tm, TP.REPAIR_PINS + ("w_mask_in",)))["E"], 4)


class PinDensity(unittest.TestCase):
    """COORD 10-23: 6 pins/um per face averaged, <= 6 in any 10-um window, alternating over 2 layers, pin/track <= 0.6"""
    def test_face_pin_layers_under_the_cap(self):
        self.assertEqual(TP.face_pin_layers("M5"), {"h": ["M4"], "v": ["M3", "M5"]})
        self.assertEqual(TP.face_pin_layers("M6"), {"h": ["M4", "M6"], "v": ["M3", "M5"]})
        self.assertEqual(TP.face_pin_layers("M7"), {"h": ["M4", "M6"], "v": ["M5", "M7"]})

    def test_one_layer_face_keeps_3_per_um(self):
        dem = {"N": 0, "S": 0, "E": 3000, "W": 3000}
        m5 = TP.content_outline(5000, [], dem, pin_layers=TP.face_pin_layers("M5"))      # E/W only M4
        m6 = TP.content_outline(5000, [], dem, pin_layers=TP.face_pin_layers("M6"))      # E/W M4 + M6
        self.assertGreaterEqual(m5["h"] - 4.32, 3000 / 3.0 - 1e-6)
        self.assertLess(m6["h"] - 4.32, 3000 / 6.0 + 2.2)
        self.assertEqual(m5["pin_cap"]["E"], 3.0)
        self.assertEqual((m6["pin_cap"]["E"], m6["pin_cap"]["N"]), (6.0, 6.0))

    def test_average_window_layers_ratio(self):
        two = TP.face_pin_layers("M6")
        ok = TP.face_pin_check("W", 502.0, [(3000, None, None)], two)
        self.assertTrue(ok["ok"], ok["why"])
        self.assertAlmostEqual(ok["ratio"], ok["peak"] / (1 / 0.048 + 1 / 0.064), places=2)
        self.assertLessEqual(ok["ratio"], TP.PIN_TRACK_RATIO_MAX)
        # same 3000 pins on ONE layer (M5 cap, E/W = M4 only): above 3/um -> FAIL
        one = TP.face_pin_check("W", 502.0, [(3000, None, None)], TP.face_pin_layers("M5"))
        self.assertFalse(one["ok"])
        self.assertTrue(any("ONE layer" in w for w in one["why"]))
        # average fine (0.5/um) but 300 pins squeezed into 20 um: the 10-um window catches it
        loc = TP.face_pin_check("N", 600.0, [(300, 100.0, 120.0)], two)
        self.assertLess(loc["avg"], 1.0)
        self.assertGreater(loc["peak"], 14.0)
        self.assertFalse(loc["ok"])
        self.assertTrue(any("window" in w for w in loc["why"]))
        # two balanced regions on the same range stack their pins
        ov = TP.face_pin_check("N", 600.0, [(40, 100.0, 300.0), (40, 100.0, 300.0)], two)
        self.assertFalse(ov["ok"])
        self.assertTrue(any("overlapping" in w for w in ov["why"]))
        # a lone clock pin inside the face region is reported, not failed
        ck = TP.face_pin_check("N", 600.0, [(1, 299.0, 301.0), (500, None, None)], two)
        self.assertTrue(ck["ok"], ck["why"])
        self.assertEqual(len(ck["overlap"]), 1)

    def test_fixed_macros_count_as_macro_area_not_std(self):
        # GEOM-REVIEW 10-23 flow bug: macros at fixed positions were folded into std ('std 80412 + macros 0')
        fx = [{"w": 60.0, "h": 50.0}] * 8
        r = TP.content_outline(2000, [], {"N": 100, "S": 100}, fixed=fx)
        self.assertIn("std 2000/", r["why"])
        self.assertEqual(r["breakdown"]["macros"], 8)
        self.assertAlmostEqual(r["breakdown"]["macro_um2"], 8 * (60 + 10.8) * (50 + 10.8), places=0)
        free = (r["w"] - 4.32) * (r["h"] - 4.32) - 8 * 60 * 50
        self.assertAlmostEqual(r["fill"], round(2000 / free, 3), places=3)

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

    def test_mixed_heights_pack_beside_the_tall_arrays(self):
        # hr_core_prompt-like: 2 tall (178 x 160) + 1 mid (175 x 70) + 4 short (66 x 18) dual-face macros
        tall, mid, short = (tm_box("t", 177.8, 160.4, "WE", 50), tm_box("m", 174.7, 70.5, "WE", 50),
                            tm_box("s", 66.3, 17.8, "WE", 20))
        ms = macros(tall, 2) + macros(mid, 1) + macros(short, 4)
        for i, m in enumerate(ms):
            m["key"] = i
        r = TP.plan_macros(300.0, 300.0, ms, {"N": 300, "S": 300, "E": 300, "W": 300})
        area = max(300.0, r["need"][0]) * max(300.0, r["need"][1])
        seq = min(max(300.0, x["need"][0]) * max(300.0, x["need"][1])
                  for x in (TP.plan_macros(300.0, 300.0, ms, {"N": 300, "S": 300, "E": 300, "W": 300}, rows=n)
                            for n in range(1, 8)))
        self.assertLessEqual(area, seq + 1e-6)
        self.assertEqual(len(r["placed"]), 7)

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

    def test_planner_version_recorded_new_kit_v2_existing_kit_v1(self):
        # COORD batch 15 condition: in-flight recipe-5 kits must not change silently; tile_plan writes the policy used
        with tempfile.TemporaryDirectory() as a:
            r, k = self.gen(a, name="tp5_v", std_area_um2=3000.0, outline=None)
            tp = json.loads(k["spec.json"])["tile_plan"]
            self.assertEqual((tp["planner_version"], tp["pin_density"], tp["pin_balance"]), (2, TP.PIN_DENSITY, True))
            self.assertEqual(json.loads(k["spec.json"])["route"]["pin_balance"], {"group_max": 1})
            # a v2 kit regenerated from its SOURCE spec (no version in it) keeps v2 (read from the kit's spec.json)
            r2 = RT.gen(str(Path(a) / "tp5_v.json"), commit="c" * 40, out_root=Path(a))
            self.assertEqual(json.loads((Path(a) / r2["kit"] / "spec.json").read_text())["tile_plan"]["planner_version"], 2)
        with tempfile.TemporaryDirectory() as a:
            r, k1 = self.gen(a, name="tp5_old", tile_plan={"planner_version": 1}, std_area_um2=3000.0, outline=None)
            kd = Path(a) / r["kit"]
            sp = json.loads(k1["spec.json"])
            self.assertEqual((sp["tile_plan"]["pin_density"], sp["tile_plan"]["pin_balance"]), (3.0, False))
            self.assertNotIn("pin_balance", sp["route"])
            for x in ("planner_version", "pin_density", "pin_balance"):     # a kit generated before TILE-FLOW2
                del sp["tile_plan"][x]
            (kd / "spec.json").write_text(json.dumps(sp, indent=1) + "\n")
            RT.gen(str(kd / "spec.json"), commit="c" * 40, out_root=Path(a))
            k2 = {f.name: f.read_text() for f in kd.iterdir()}
            self.assertEqual(json.loads(k2["spec.json"])["tile_plan"]["planner_version"], 1)
            self.assertEqual({n: v for n, v in k1.items() if n != "spec.json"},
                             {n: v for n, v in k2.items() if n != "spec.json"})
            self.assertNotIn("pin_layers", json.loads(k2["floorplan.json"])["tile_plan"])

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
            # a stale derived value carried in the spec's orfs_vars never wins over unregistered_ok
            r, k = self.gen(a, name="tp5_v", std_area_um2=3000.0, outline=None, orfs_vars={"OT_FENCE_UNREG_OK": "old"},
                            unregistered_ok={"sr": "status strap read by the die once at boot"})
            self.assertIn("OT_FENCE_UNREG_OK=sr", k["kit.env"])
            self.assertNotIn("OT_FENCE_UNREG_OK=old", k["kit.env"])

    def test_explicit_big_outline_fails_without_reason(self):
        with tempfile.TemporaryDirectory() as a:
            r, _ = self.gen(a, name="tp5_b", std_area_um2=1500.0, outline={"w": 500.0, "h": 500.0})
            fails = [f for f in r["findings"] if f[1] == "outline_ratio"]
            self.assertEqual(fails[0][0], "FAIL")
            r, _ = self.gen(a, name="tp5_c", std_area_um2=1500.0, outline={"w": 500.0, "h": 500.0},
                            outline_reason="die slot hole: pins abut the neighbours")
            self.assertEqual([f[0] for f in r["findings"] if f[1] == "outline_ratio"], ["INFO"])

    def test_pin_generator_alternates_two_layers(self):
        with tempfile.TemporaryDirectory() as a:
            r, k = self.gen(a, name="tp5_pb", std_area_um2=3000.0, outline=None)
            self.assertIn("export OT_PIN_GROUP_MAX=1", k["kit.env"])          # layer alternates pin by pin
            self.assertIn("export OT_PIN_BALANCE_V='M3 M5'", k["kit.env"])
            self.assertIn("export OT_PIN_BALANCE_H='M4'", k["kit.env"])        # M5 cap: one E/W layer -> 3/um there
            self.assertFalse([f for f in r["findings"] if f[1] == "pin_density" and f[0] == "FAIL"])
            r, k = self.gen(a, name="tp5_pb6", std_area_um2=3000.0, outline=None, layer_cap="M6",
                            layer_cap_grant="TEST: tile_plan 6 pins/um on E/W M4+M6")
            self.assertIn("export OT_PIN_BALANCE_H='M4 M6'", k["kit.env"])
            tp = json.loads(k["floorplan.json"])["tile_plan"]
            self.assertEqual(tp["pin_layers"], {"h": ["M4", "M6"], "v": ["M3", "M5"]})
            self.assertEqual(tp["pin_cap"]["W"], 6.0)

    def test_pin_density_fail_on_dense_range(self):
        with tempfile.TemporaryDirectory() as a:
            # 'pdata' etc. squeezed into a 2-um range of the S face: window peak far above 6/um -> FAIL
            from unittest import mock
            with mock.patch.object(TP, "port_widths", return_value={"pdata": 256, "pv": 1, "pgi": 8, "pbeat": 4,
                                                                    "sr": 1, "clk": 1, "rst_n": 1, "ra": 16}):
                r, _ = self.gen(a, name="tp5_pd", std_area_um2=3000.0, outline=None,
                                pin_ranges={"pdata": [10.0, 12.0]})
            f = [x for x in r["findings"] if x[1] == "pin_density"]
            self.assertTrue(f and f[0][0] == "FAIL", f)

    def test_rg3b_spec_counts_srams_as_macros(self):
        # GEOM-REVIEW 10-23: s81dv_rg3b_xm6 (8 x ot_sram_1r1w_1024x256 at fixed 'at') said 'std 80412 um2 + macros 0'
        with tempfile.TemporaryDirectory() as a:
            sp = json.loads((HERE / "examples" / "s81dv_rg3b_xm6_tp.json").read_text())
            p = Path(a) / "xm6.json"
            p.write_text(json.dumps(sp))
            r = RT.gen(str(p), commit="c" * 40, out_root=Path(a))
            tp = json.loads((Path(a) / r["kit"] / "floorplan.json").read_text())["tile_plan"]
            lef = RT.track_macro("physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2")
            w, h = lef["W"] / 1000, lef["H"] / 1000
            self.assertEqual(tp["breakdown"]["macros"], 8)
            self.assertAlmostEqual(tp["breakdown"]["macro_um2"], 8 * (w + 10.8) * (h + 10.8), delta=1.0)
            self.assertIn(f"std {sp['std_area_um2']:.0f}/", tp["why"])      # std = synthesized std cells only
            self.assertLess(tp["breakdown"]["logic_um2"], 2 * sp["std_area_um2"] / 0.65)
            self.assertLess(tp["fill"], 0.2)

    def test_tile_plan_off_keeps_recipe_4_behaviour(self):
        with tempfile.TemporaryDirectory() as a:
            _, k = self.gen(a, name="tp5_off", tile_plan=False)
            self.assertNotIn("pin_reg_face_fence", k["kit.env"] + k.get("pre_gpl.tcl", ""))


if __name__ == "__main__":
    unittest.main()
