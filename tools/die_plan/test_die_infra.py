#!/usr/bin/env python3
"""unit tests: tools/die_plan/die_infra.py (python3 -m pytest tools/die_plan/test_die_infra.py)"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_infra as DI  # noqa: E402

LAYERS = {"M8": {"dir": "H", "pitch_um": 0.08}, "M9": {"dir": "V", "pitch_um": 0.08}}


def plan(W=108.0, H=108.0, grid=None):
    return SimpleNamespace(W=W, H=H, name="t", layers=LAYERS, die={"pg": {"grid": grid or []}})


class T(unittest.TestCase):
    def test_fixed_mesh_cannot_short_or_violate_pg_spacing(self):
        P = plan()
        pg = [("VDD", "M9", 4.08, 0, 4.56, 108), ("VSS", "M9", 8.4, 0, 8.88, 108)]
        clock = [("ck_mesh_r0", "M9", 4.24, 0, 4.4, 108, .16)]
        r = DI.pg_clock_conflicts(P, pg, clock)
        self.assertEqual((r["conflicts"], r["metal_shorts"]), (1, 1))
        # Real separated tracks pass; a different metal layer also passes.
        self.assertEqual(DI.pg_clock_conflicts(P, pg, [("ck_mesh", "M9", 6, 0, 6.16, 108, .16)])["verdict"], "PASS")
        self.assertEqual(DI.pg_clock_conflicts(P, pg, [("ck_mesh", "M8", 4.24, 0, 4.4, 108, .16)])["verdict"], "PASS")
        # No metal overlap but only40nm separation is still invalid for80nm NDR.
        r = DI.pg_clock_conflicts(P, pg, [("ck_mesh", "M9", 4.60, 0, 4.76, 108, .16)])
        self.assertEqual((r["conflicts"], r["metal_shorts"]), (1, 0))

    def test_snap_moves_special_wires_off_pg_onto_free_tracks(self):
        # KV-INFRA-R2: a clock strap built against an older PG grid and a reset L-route both sit on a PG stripe;
        # the snap moves each across its axis to the nearest PG-free track centre, length/width unchanged.
        P = plan()
        pg = [("VDD", "M9", 4.08, 0, 4.56, 108), ("VSS", "M9", 8.4, 0, 8.88, 108), ("VDD", "M8", 0, 20.0, 108, 20.48)]
        wires = [("ck_mesh_r0", "M9", 4.24, 0, 4.4, 108, .16), ("rst", "M8", 10, 20.2, 60, 20.24, .04),
                 ("ok", "M9", 6.0, 0, 6.16, 108, .16), ("m7", "M7", 4.24, 0, 4.4, 108, .16)]
        self.assertEqual(DI.pg_clock_conflicts(P, pg, wires[:2], clearance_um=0.08)["metal_shorts"], 2)
        out, led = DI.snap_off_pg(P, pg, wires, 0.08, max_shift_um=2.0)
        self.assertEqual((led["moved"], led["unsnappable"]), (2, 0))
        self.assertEqual(out[2:], wires[2:])                       # clear wire and non-PG layer untouched
        self.assertEqual(DI.pg_clock_conflicts(P, pg, out[:2], clearance_um=0.08)["conflicts"], 0)
        for a, b in zip(wires[:2], out[:2]):
            self.assertAlmostEqual(a[4] - a[2], b[4] - b[2])          # same width / length
            self.assertAlmostEqual(a[5] - a[3], b[5] - b[3])
        c = (out[0][2] + out[0][4]) / 2                            # on a track centre (pitch 0.08, offset 0)
        self.assertAlmostEqual(c / 0.08, round(c / 0.08), places=6)
        self.assertLessEqual(led["max_shift_um"], 0.6)
        # a limit smaller than the needed move leaves the wire in place and reports it
        _, led = DI.snap_off_pg(P, pg, wires[:1], 0.08, max_shift_um=0.05)
        self.assertEqual((led["moved"], led["unsnappable"]), (0, 1))

    def test_infra_pg_phy_window_power_from_load_model_rows(self):
        # KV-INFRA-R2: load_model hands phy_power its window rows as {name, rect, part, iface}; a generic PHY
        # window (not SerDes / UCIe) is charged PHY_W_MM2 x its area instead of failing on a missing rect_um.
        import infra_pg as IP
        P = SimpleNamespace(parts={}, types={})
        w, basis = IP.phy_power(P, dict(name="io_phy_EN_0", rect=[0, 0, 1000.0, 1000.0], part=None, iface="phy"), 4.37)
        self.assertAlmostEqual(w, IP.PHY_W_MM2 * 1.0)
        w2, _ = IP.phy_power(P, dict(name="x", rect_um=[0, 0, 500.0, 1000.0], iface="phy"), 4.37)
        self.assertAlmostEqual(w2, IP.PHY_W_MM2 * 0.5)

    def test_regional_preroute_preserves_physical_clock_cuts(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            m = dict(meta=dict(ndr="4w", regions_depth=1, regions=[
                dict(k=0, i0=0, i1=2, j0=0, j1=2, strap_box_um=[0, 0, 49, 100]),
                dict(k=1, i0=2, i1=4, j0=0, j1=2, strap_box_um=[51, 0, 100, 100])]),
                xs=[10, 40, 60, 90], ys=[10, 90])
            (d / "mesh.json").write_text(json.dumps(m))
            _, rects = DI.clock_rects(d, None)
            self.assertEqual({r[0] for r in rects}, {"ck_mesh_r0", "ck_mesh_r1"})
            self.assertEqual(len(rects), 8)
            # A reconstructed full strap would cross this seam and short the
            # independently driven regions. Preserve the deliberate NDR gap.
            for net, layer, x0, y0, x1, y1, width in rects:
                if net == "ck_mesh_r0": self.assertLess(x1, 50)
                else: self.assertGreater(x0, 50)
            m["meta"].pop("regions")
            (d / "mesh.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "missing.*region"):
                DI.clock_rects(d, None)

    def test_trim_pads_die_absorbs_residual(self):
        k, res = DI.trim_pads({"a": 30.0, "b": 0.0, "c": -12.0}, 10.0)
        self.assertEqual(k, {"a": 0, "b": 3, "c": 4})       # the latest tile gets none; others delayed to match
        self.assertLessEqual(max(abs(v) for v in res.values()), 5.0)
        self.assertEqual(DI.trim_pads({}, 10.0), ({}, {}))

    def test_trim_pads_reserve_two_sided(self):
        k, res = DI.trim_pads({"slow": 20.0, "nom": 0.0, "fast": -20.0, "way_slow": 50.0}, 10.0, reserve=2)
        self.assertEqual(k, {"slow": 0, "nom": 2, "fast": 4, "way_slow": 0})
        self.assertEqual(res["way_slow"], -30.0)          # beyond the reserve: reported, not silently dropped
        self.assertEqual(res["nom"], 0.0)

    def test_trim_end_to_end_netlist_and_offsets(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "m"
            d.mkdir()
            taps = [dict(part="pa", tap="clk", port="t_pa__clk", xy=[10, 10], stub="ckm_s_0"),
                    dict(part="pb", tap="clk", port="t_pb__clk", xy=[50, 10], stub="ckm_s_1")]
            (d / "mesh.json").write_text(json.dumps(dict(meta=dict(ndr="4w", cells=3), xs=[0, 100], ys=[0, 100],
                                                         taps=taps)))
            cells = {"ckm_d_0_0_0": dict(x=0, y=0, kind="drv"), "ckm_s_0": dict(x=10, y=0, kind="stub"),
                     "ckm_s_1": dict(x=50, y=0, kind="stub")}
            (d / "place.json").write_text(json.dumps(cells))
            nets = [dict(name="root", drv="port:root", loads=["ckm_d_0_0_0"]),
                    dict(name="t_pa__clk", drv="ckm_s_0", loads=["port:t_pa__clk"]),
                    dict(name="t_pb__clk", drv="ckm_s_1", loads=["port:t_pb__clk"])]
            ports = [["input", "root"], ["output", "t_pa__clk"], ["output", "t_pb__clk"]]
            (d / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)))
            off = Path(td) / "off.json"
            off.write_text(json.dumps({"pa": 25.0}))           # tile pa measured 25 ps slower than plan
            o = Path(td) / "o"
            DI.main(["trim", str(d), "--offsets", str(off), "--out", str(o), "--quantum-ps", "10"])
            v = (o / "ctree.v").read_text()
            M = json.loads((o / "mesh.json").read_text())
            self.assertEqual(M["meta"]["trim"]["pads"], 2)       # pb gets round(25/10) = 2 pads, pa none
            self.assertIn(".A(ck_mesh), .Y(t_pa__clk)", v)       # pa's stub still drives its tap directly
            self.assertNotIn(".A(ck_mesh), .Y(t_pb__clk)", v)    # pb's stub now drives the trim chain
            self.assertIn(".Y(t_pb__clk)", v)
            self.assertEqual(json.loads((o / "tap_offsets.json").read_text())["t_pa__clk"], 25.0)

    def test_guides_parse_and_centreline_wire(self):
        with tempfile.TemporaryDirectory() as td:
            g = Path(td) / "r.guide"
            g.write_text("n1\n(\n0 0 54000 10800 M8\n43200 0 54000 32400 M9\n0 0 10800 10800 M7\n)\n")
            G = DI.read_guides(g)
            self.assertEqual(len(G["n1"]), 3)
            L, *b = G["n1"][0]
            x0, y0, x1, y1 = DI.guide_wire(L, *b, 0.16)
            self.assertAlmostEqual(y0 + y1, 10.8)             # centreline of the gcell row
            self.assertAlmostEqual(y1 - y0, 0.16)
            self.assertAlmostEqual(x0, 5.4)                    # gcell centre to gcell centre
            L, *b = G["n1"][1]
            x0, y0, x1, y1 = DI.guide_wire(L, *b, 0.16)
            self.assertAlmostEqual(x1 - x0, 0.16)
            self.assertAlmostEqual(y1 - y0, 21.6)

    def test_pg_rects_nets_and_tracks(self):
        P = plan(grid=[dict(layer="M9", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"])])
        R = DI.pg_rects(P, DI.pg_grid(P))
        self.assertEqual({r[0] for r in R}, {"VDD", "VSS"})
        self.assertTrue(all(r[1] == "M9" and r[3] == 0 and r[5] == 108.0 for r in R))
        tr = DI.track_use(P, [("pg", r[1], r[2] - 0.04, r[3], r[4] + 0.04, r[5]) for r in R])
        # 0.56 um footprint = 7 tracks per stripe; 24 stripes (every 4.32 um, the last one off the die) / 1350 tracks
        self.assertEqual(len(R), 24)
        self.assertAlmostEqual(tr["M9"]["pg"], 24 * 7 / 1350, places=4)
        self.assertEqual(tr["M8"]["all"], 0.0)

    def test_region_limited_pg_row(self):
        P = plan(grid=[dict(layer="M8", width_um=0.48, pitch_um=10.8, offset_um=5.4, nets=["VDD"],
                            rect_um=[0, 0, 54, 54])])
        R = DI.pg_rects(P, DI.pg_grid(P))
        self.assertTrue(all(r[4] == 54 and r[5] <= 54 for r in R))

    def test_l_rects_and_footprint(self):
        r = DI.l_rects((0, 0), (100, 50), 0.04)
        self.assertEqual([x[0] for x in r], ["M8", "M9"])
        fp = DI.footprint("M8", r[0][1:], 0.04, 0.04)
        self.assertAlmostEqual(fp[3] - fp[1], 0.12)

    def test_strip_route(self):
        v = "module x_route (rst_n);\n  input rst_n;\n  A u0 (.arst_n(rst_n), .f_i(w), .f_o(w));\n  B u1 (.arst_n(rst_n));\nendmodule\n"
        s = DI.strip_route(v)
        self.assertIn("A u0 ();", s)
        self.assertIn("B u1 ();", s)

    def test_write_def_fixed_specialnets(self):
        P = plan()
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "p.def"
            DI.write_def(P, f, [("VDD", "pg", "M9", 4.08, 0, 4.56, 108, "STRIPE"),
                                ("ck_mesh", "clock", "M8", 0, 9.92, 100, 10.08, "STRIPE"),
                                ("rstw_a_rst_o_0", "reset", "M8", 0, 1.98, 30, 2.02, "IOWIRE")])
            t = f.read_text()
            self.assertIn("SPECIALNETS 3 ;", t)
            self.assertIn("+ FIXED M9 480 + SHAPE STRIPE ( 4320 0 ) ( 4320 108000 )", t)
            self.assertIn("+ USE CLOCK", t)
            self.assertIn("+ USE RESET", t)

    def test_parse_grt(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "grt.log"
            f.write_text("[INFO GRT-0096] Final congestion report:\nLayer         Resource        Demand        Usage (%)    "
                         "Max H / Max V / Total Overflow\n-----\nM4   1000   10   1.00%   0 / 0 / 0\n"
                         "M8   500   20   4.00%   1 / 0 / 3\nTotal  1500  30  2.00%  1 / 0 / 3\nEXIT 0\n")
            r = DI.parse_grt(f)
            self.assertEqual(r["total_overflow"], 3)
            self.assertEqual(r["layers"]["M8"]["overflow"], 3)
            self.assertEqual(r["exit"], "0")
            self.assertEqual(r["verdict"], "FAIL")

    def test_incomplete_or_crashed_grt_cannot_report_zero_overflow(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "grt.log"
            for txt, verdict in (("starting route\n", "NOT RUN"),
                                 ("[ERROR GRT-0113] no routing\nEXIT 1\n", "FAIL"),
                                 ("EXIT 0\n", "NOT RUN")):
                f.write_text(txt)
                r = DI.parse_grt(f)
                self.assertIsNone(r["total_overflow"])
                self.assertEqual(r["verdict"], verdict)

    def test_die_gate_cannot_run_five_iteration_diagnostic(self):
        with self.assertRaisesRegex(ValueError, "at least 50"):
            DI.cmd_grt(SimpleNamespace(iterations=5))


if __name__ == "__main__":
    unittest.main()
