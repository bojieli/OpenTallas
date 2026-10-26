#!/usr/bin/env python3
"""unit tests: tools/die_plan/die_clock_mesh.py site helpers (python3 -m pytest tools/die_plan/test_die_clock_mesh.py)"""
import sys
import unittest
import tempfile
import json
import os
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_mesh as CM  # noqa: E402


class Box:
    """keep-out index stand-in: one blocked rect."""
    def __init__(self, r):
        self.r = r

    def hit(self, x, y, m=0.0):
        x0, y0, x1, y1 = self.r
        return x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m


class T(unittest.TestCase):
    def test_leg_sites_free_leg_equal_hops(self):
        out = dict(unplaced=[])
        pts = CM.leg_sites(Box((-10, -10, -9, -9)), (0, 0), (2000, 0), 450.0, out, "h0")
        xs = [0.0] + [p[0][0] for p in pts] + [2000.0]
        hops = [b - a for a, b in zip(xs, xs[1:])]
        self.assertEqual(len(pts), 4)
        self.assertLessEqual(max(hops), 450.0 + 1e-6)
        self.assertLess(max(hops) - min(hops), 1.0)

    def test_leg_sites_blocked_never_exceeds_seg_on_leg(self):
        out = dict(unplaced=[])
        pts = CM.leg_sites(Box((300, -50, 700, 50)), (0, 0), (2000, 0), 450.0, out, "h0")
        xs = [0.0] + [p[0][0] for p in pts] + [2000.0]
        self.assertTrue(all(not (300 - 3 <= x <= 700 + 3) for x in xs[1:-1]))
        self.assertLessEqual(max(b - a for a, b in zip(xs, xs[1:])), 450.0 + 1e-6)

    def test_stub_foot_shortest(self):
        xs, ys = [100.0, 300.0, 500.0], [100.0, 300.0, 500.0]
        q, d, axis, i, j = CM.stub_foot(Box((0, 280, 600, 320)), xs, ys, 290.0, 310.0, 500.0)
        self.assertIsNotNone(q)
        self.assertEqual((axis, i), (1, 1))          # the M8 strap y=300 is blocked; M9 x=300 slid off the box
        self.assertLessEqual(abs(q[0] - 290) + abs(q[1] - 310), 30.0)

    def test_region_boxes_follow_htree_bisection(self):
        R = CM.region_boxes(8, 8, 3, W=800.0, H=800.0)
        self.assertEqual(len(R), 8)
        cells = {(i, j) for g in R for i in range(g["i0"], g["i1"]) for j in range(g["j0"], g["j1"])}
        self.assertEqual(len(cells), 64)                       # a partition of the intersection grid
        for g in R:                                            # region tag = the H-tree tag prefix of its members
            for i in range(g["i0"], g["i1"]):
                for j in range(g["j0"], g["j1"]):
                    self.assertTrue(CM.htree_tag(i, j, 8, 8).startswith(g["tag"]))
        self.assertEqual(R[0]["box_um"], [0.0, 0.0, 200.0, 400.0])   # x, y, x halvings
        self.assertEqual(CM.region_boxes(8, 8, 0)[0]["tag"], "h")

    def test_dataflow_cohort_cuts_match_real_xx_tree_tags(self):
        _, edges = CM.cohort_axis_grid(8, 800., [100., 300., 650.], 2)
        R = CM.region_boxes(8, 8, 2, W=800., H=800., axes="xx", x_edges=edges)
        self.assertEqual([g["box_um"] for g in R], [[0.,0.,100.,800.], [100.,0.,300.,800.],
                                                    [300.,0.,650.,800.], [650.,0.,800.,800.]])
        for g in R:
            for i in range(g["i0"],g["i1"]):
                for j in range(8):
                    self.assertTrue(CM.htree_tag(i,j,8,8,"xx").startswith(g["tag"]))

    def test_floorplan_regions_on_partition_edges(self):
        xs, R = CM.floorplan_regions(dict(x_cuts_um=[700., 900.], region_nx=[4, 1, 4]), 1600., 800., 4)
        self.assertEqual(len(xs), 9)
        self.assertEqual([g["box_um"][0] for g in R], [0., 700., 900.])
        self.assertEqual([g["tag"] for g in R], ["h0", "h1", "h2"])
        self.assertTrue(all(700. < x < 900. for x in xs[R[1]["i0"]:R[1]["i1"]]))
        for g in R:
            for i in range(g["i0"], g["i1"]):
                for j in range(4):
                    self.assertTrue(CM.floorplan_tag(i, j, R, 4).startswith(g["tag"]))
        with self.assertRaises(ValueError):
            CM.floorplan_regions(dict(x_cuts_um=[700.], region_nx=[3, 4]), 1600., 800., 4)

    def test_macro_hole_clips_strap_end_never_splits(self):
        hole = [dict(name="PHY", rect_um=[600., 600., 1000., 800.])]
        self.assertEqual(CM.clip_span(0., 700., 700., 0, hole, 0.5), (0., 599.5))       # row ends at the macro edge
        self.assertEqual(CM.clip_span(0., 700., 500., 0, hole, 0.5), (0., 700.))        # row below the macro: untouched
        self.assertIsNone(CM.clip_span(700., 900., 700., 0, hole, 0.5))                  # wholly inside: removed
        self.assertEqual(CM.clip_span(0., 800., 800., 1, hole, 0.5), (0., 599.5))       # column stops at the macro
        with self.assertRaises(ValueError):
            CM.clip_span(0., 1600., 700., 0, hole, 0.5)                                  # would split: refuse

    def test_floorplan_build_holes_prune_and_explicit_regions(self):
        types = dict(ta=dict(hard_cores=[dict(inst="core", origin_um=[400., 100.], outline_um=[250., 500.],
                                              obs_max="M5")]), tb={}, tc={})
        rects = dict(A=(0., 0., 700., 800.), B=(700., 0., 900., 600.), C=(900., 0., 1600., 800.),
                     PHY=(600., 600., 1000., 800.))
        P = SimpleNamespace(W=1600., H=800., clock={}, types=types, layer_budget=dict(partition_signal_max="M7"),
                            parts=dict(A=dict(type="ta"), B=dict(type="tb"), C=dict(type="tc")),
                            rect=lambda n: rects[n], to_die=lambda n, xy: xy)
        ko = [(400., 100., 650., 600., "A/core"), (600., 600., 1000., 800., "io/PHY")]
        fp = dict(x_cuts_um=[700., 900.], region_nx=[2, 1, 2], macro_holes=[dict(name="PHY", rect_um=list(rects["PHY"]))],
                  hard_core_drivers="drop")
        taps = [("A", "clk", 300., 300., 0.), ("B", "clk", 790., 300., 0.), ("C", "clk", 1200., 300., 0.)]
        with patch.object(CM.DC, "keepouts", return_value=ko), patch.object(CM.DC, "plan_taps", return_value=taps), \
                patch.object(CM.DC, "plan_tap_early", return_value={}):
            cells, nets, ports, M = CM.build(P, 4, 4, m=1, max_move=50., region_edge_straps=True, floorplan=fp)
        self.assertEqual(M["unplaced"], [])
        self.assertEqual([g["tag"] for g in M["meta"]["regions"]], ["h0", "h1", "h2"])
        self.assertEqual(M["part_region"], dict(A=0, B=1, C=2))
        kinds = {(v[0], v[1]): v[2] for v in M["hole_drivers"]}
        self.assertEqual(kinds[(2, 3)], "macro_hole")                    # centre column top row: under the PHY
        self.assertIn("hard_core", kinds.values())                       # x=525 rows inside the core: driverless
        self.assertIsNone(M["strap_spans"]["H:3:1"])                      # centre top row wholly in the hole
        self.assertLess(M["strap_spans"]["V:2:1"][1], 600.)               # centre column stops at the macro edge
        self.assertIn("h111", M["pruned_branches"])                       # dead centre-top leaf pruned
        for c in cells.values():                                          # no clock cell inside the macro hole
            self.assertFalse(CM.in_rect(rects["PHY"], c["x"], c["y"]))
        loads = {ld for n in nets for ld in n["loads"]}
        undriven = [c for c, v in cells.items() if c != "ckm_n0" and v["kind"] != "stub" and c not in loads]
        self.assertEqual(undriven, [])                                     # every tree cell is driven (stubs: mesh)
        self.assertEqual(CM.floorplan_tag(3, 0, M["meta"]["regions"], 4)[:2], "h2")

    def test_free_along_bounds(self):
        K = Box((90, -5, 110, 5))
        q, d = CM.free_along(K, (100.0, 0.0), 0, 50.0)
        self.assertIsNotNone(q)
        q, d = CM.free_along(K, (100.0, 0.0), 0, 50.0, bounds=(0.0, 100.0))
        self.assertLess(q[0], 90.0)                            # never slides past the region's strap end

    def test_stub_foot_region_box(self):
        xs, ys = [100.0, 300.0, 500.0, 700.0], [100.0, 300.0, 500.0, 700.0]
        far = Box((-10, -10, -9, -9))
        q, d, axis, i, j = CM.stub_foot(far, xs, ys, 410.0, 410.0, 500.0)
        self.assertTrue(i >= 2 or j >= 2)                      # unconstrained: the nearer x=500 / y=500 straps
        q, d, axis, i, j = CM.stub_foot(far, xs, ys, 410.0, 410.0, 500.0, box=(0, 2, 0, 2))
        self.assertTrue(q[0] <= 300.0 + 1e-6 and q[1] <= 300.0 + 1e-6)   # region box: own straps, own extent
        self.assertTrue(i < 2 and j < 2)

    def test_mesh_net_names(self):
        self.assertEqual(CM.mesh_net(None), "ck_mesh")         # default (no --regions) unchanged
        self.assertEqual(CM.mesh_net(3), "ck_mesh_r3")

    def test_region_edge_strap_reaches_legal_driver_without_crossing_boundary(self):
        xs, ys = [100., 300., 500., 700.], [100., 300., 500., 700.]
        g = dict(i0=0, i1=2, j0=0, j1=4, strap_box_um=[.214, .214, 399.786, 799.786])
        obstacle = Box((200, -20, 340, 820))
        q, _ = CM.free_along(obstacle, (300, 100), 0, 60, bounds=(100, 300))
        self.assertIsNone(q)
        q, _ = CM.free_along(obstacle, (300, 100), 0, 60, bounds=CM.strap_bounds(g, xs, ys, 0))
        self.assertGreater(q[0], 340.)
        self.assertLess(q[0], 400.)
        foot, *_ = CM.stub_foot(obstacle, xs, ys, 350, 110, 60, box=(0, 2, 0, 4), extent=g["strap_box_um"])
        self.assertGreater(foot[0], 340.)
        self.assertLess(foot[0], 400.)

    def test_clock_cells_are_physical_obstacles_and_abutment_is_legal(self):
        K = CM.DC.KeepIndex([], die=(100., 100.))
        cells = dict(a=dict(x=10., y=10.), b=dict(x=10.+CM.BUF_W, y=10.))
        CM.reserve_cell(K, "a", cells["a"])
        self.assertIsNotNone(K.hit(10.5, 10.1, m=0.))
        self.assertEqual(CM.placement_overlaps(cells), [])
        cells["b"]["x"] -= .054
        self.assertEqual(CM.placement_overlaps(cells), [["a", "b"]])

    def test_failed_first_corner_is_not_hidden_by_successful_second_corner(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td); kit = d / "kit"; (kit / "grt").mkdir(parents=True); (kit / "abstracts").mkdir()
            (kit / "grt/route.v").write_text("module route(rst); input rst; endmodule\n")
            (kit / "grt/grt.tcl").write_text("read_verilog /work/grt/route.v\nlink_design route\nsource /work/grt/obs.tcl\n")
            (d / "ctree.v").write_text("module die_ctree(root,t_pin); input root; output t_pin; assign t_pin=root; endmodule\n")
            (d / "place.json").write_text("{}")
            (d / "nets.json").write_text('{"nets": []}')
            (d / "mesh.json").write_text(json.dumps(dict(meta=dict(ndr="4w", W=10, H=10, root_um=[1, 1]),
                                                         xs=[2, 8], ys=[2, 8], taps=[dict(port="t_pin",xy=[5,5])])))
            CM.cmd_combo(SimpleNamespace(dir=str(d), kit=str(kit)))
            self.assertIn("-layer M7 -location {5.000 5.000} -pin_size {0.032 0.768}", (d/"combo.tcl").read_text())
            fake = d / "bin"; fake.mkdir()
            docker = fake / "docker"
            docker.write_text('#!/bin/bash\nfor a in "$@"; do case "$a" in CORNER=TT) exit 7;; CORNER=FF) exit 0;; esac; done\nexit 9\n')
            docker.chmod(0o755)
            r = subprocess.run(["bash", str(d / "run_combo.sh")], env=dict(os.environ, PATH=str(fake)+":"+os.environ["PATH"]))
            self.assertEqual(r.returncode, 7)

    def test_pg_snap_uses_real_track_phase_and_rejects_impossible_ndr(self):
        # Actual sized-QC M9 grid: .48-um stripes every .864 um (VDD/VSS alternate), real kit tracks .08/.04.
        shapes = [("VDD" if i % 2 == 0 else "VSS", "M9", .864*i-.24, 0., .864*i+.24, 10.) for i in range(8)]
        profile = dict(pitch_um=.08, offset_um=.04)
        xs = CM.pg_free_axis([2.16, 4.32], shapes, "M9", 0, 6., profile, .08, .08, 1.)
        for x in xs:
            self.assertAlmostEqual((x-.04)/.08, round((x-.04)/.08))
            self.assertTrue(all(x+.08+.08 <= r[2] or x-.08-.08 >= r[4] for r in shapes))
        # 8W needs .32+2*.08=.48 um while only .384 um remains between adjacent PG metal stripes.
        with self.assertRaisesRegex(ValueError, "no PG-free"):
            CM.pg_free_axis([2.16], shapes, "M9", 0, 6., profile, .16, .08, 1.)

    def test_unplaceable_clock_repeater_keeps_legal_short_tail_but_fails_long_tail(self):
        for end, structural in ((783., False), (950., True)):
            cells = dict(d=dict(x=50., y=500., kind="stub"))
            nets = [dict(name="wire", drv="d", loads=["port:t"], level=99)]
            K = CM.DC.KeepIndex([(100., 0., 800., 1000., "PHY")], die=(1000., 1000.))
            out = dict(unplaced=[])
            def illegal(*args, **kwargs):
                self.fail("must never create a repeater inside the PHY")
            added = CM.split_long(cells, nets, K, {"t": (end, 500.)}, 480., illegal, out)
            self.assertEqual(added, 0)
            self.assertEqual(nets[0]["loads"], ["port:t"])
            self.assertEqual(bool(out["unplaced"]), structural)

    def test_floorplan_tail_tries_y_first_l_through_channel(self):
        # node in a vertical channel (x 600-700), driver in a row gap (y 1000-1020); the x-first L crosses the core
        ko = [(0., 0., 600., 1000., "c0"), (700., 0., 1400., 1000., "c1"), (0., 1020., 1400., 2000., "c2")]
        for both, splits in ((False, 0), (True, 1)):
            cells = dict(n=dict(x=650., y=500., kind="node"), d=dict(x=200., y=1010., kind="drv"))
            nets = [dict(name="w", drv="n", loads=["d"], level=9)]
            K = CM.DC.KeepIndex(ko, die=(1400., 2000.))
            out = dict(unplaced=[])
            made = []
            def cell(name, x, y, kind, **kw):
                made.append((x, y)); cells[name] = dict(x=x, y=y, kind=kind); return name
            self.assertEqual(CM.split_long(cells, nets, K, {}, 480., cell, out, both_l=both), splits)
            self.assertEqual(bool(out["unplaced"]), not both)
            for x, y in made:
                self.assertIsNone(K.hit(x, y, m=0.))

    def test_floorplan_tail_single_repeater_within_reach(self):
        # 770-um straight tail whose midpoint sits in a 600-um macro: one legal repeater near the start keeps both
        # hops inside the 750-um reach; without both_l the tail is structural
        ko = [(100., 0., 700., 1000., "macro")]
        for both in (False, True):
            cells = dict(n=dict(x=10., y=500., kind="node"), d=dict(x=780., y=500., kind="drv"))
            nets = [dict(name="w", drv="n", loads=["d"], level=9)]
            out = dict(unplaced=[])
            made = []
            def cell(name, x, y, kind, **kw):
                made.append((x, y)); cells[name] = dict(x=x, y=y, kind=kind); return name
            CM.split_long(cells, nets, CM.DC.KeepIndex(ko, die=(1000., 1000.)), {}, 480., cell, out, both_l=both)
            self.assertEqual(bool(out["unplaced"]), not both)
            if both:
                (x, y), = made
                self.assertLessEqual(max(abs(x - 10.), abs(780. - x)) + CM.BUF_W + CM.ROW_Y, 750.)

    def test_floorplan_tail_detours_around_a_wall(self):
        ko = [(300., 0., 1300., 1600., "wall")]
        K = CM.DC.KeepIndex(ko, die=(2000., 2000.))
        cells = dict(n=dict(x=200., y=800., kind="node"), d=dict(x=1400., y=800., kind="drv"))
        nets = [dict(name="w", drv="n", loads=["d"], level=9)]
        out = dict(unplaced=[])
        made = []
        def cell(name, x, y, kind, **kw):
            made.append((x, y)); cells[name] = dict(x=x, y=y, kind=kind); return name
        CM.split_long(cells, nets, K, {}, 480., cell, out, both_l=True)
        self.assertEqual(out["unplaced"], [])
        pts = [(200., 800.)] + made + [(1400., 800.)]
        self.assertTrue(all(K.hit(x, y, m=0.) is None for x, y in made))
        self.assertLessEqual(max(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:])), 480.)

    def test_island_window_is_a_legal_driver_site_only_in_its_own_core(self):
        wins = [(100., 200., 108.64, 204.32, "P/core_a"), (400., 200., 408.64, 204.32, "P/core_b")]
        site = CM.island_site(wins, "P/core_a", 130., 230., 250., 60., lambda ax: (0., 1000.))
        (cx, cy), foot, axis, slide, jog = site
        self.assertEqual((cx, cy), (104.32, 202.16))
        self.assertLessEqual(jog, 60.)
        self.assertEqual(foot[axis], (cx, cy)[axis])                  # the foot lies on the strap through the window
        self.assertIsNone(CM.island_site(wins, "P/core_c", 130., 230., 250., 60., lambda ax: (0., 1000.)))
        P = SimpleNamespace(W=1000., H=1000.)
        cells = dict(d=dict(x=101., y=201., kind="drv"), r=dict(x=101., y=201.5, kind="rep"))
        with patch.object(CM.DC, "keepouts", return_value=[(50., 50., 300., 300., "P/core_a")]):
            bad = CM.hard_keepout_violations(P, cells, wins)
        self.assertEqual([b["cell"] for b in bad], ["r"])           # islands hold clock drivers only

    def test_hard_keepout_census_checks_the_whole_real_cell_body(self):
        P = SimpleNamespace(W=100., H=100.)
        with patch.object(CM.DC, "keepouts", return_value=[(11.5, 0., 20., 100., "macro")]):
            # BUF24 width 1.62 reaches the macro despite its left edge and centre lying outside it.
            bad = CM.hard_keepout_violations(P, dict(near=dict(x=10., y=20.)))
            self.assertEqual(bad[0]["cell"], "near")
            self.assertEqual(CM.hard_keepout_violations(P, dict(far=dict(x=9., y=20.))), [])

    def test_core_offsets_compare_sinks_at_each_corner(self):
        M = {"taps": [dict(part="p", tap="core", port="tc", early_ps=100),
                      dict(part="p", tap="ordinary", port="to", early_ps=0)]}
        offsets = {("p", "core"): {"TT": 100, "FF": 70}}
        for corner, core_arrival in (("TT", 900), ("FF", 930)):
            late, early, _ = CM.sink_arrivals(M, {"tc": (core_arrival, core_arrival - 5, 10),
                                                 "to": (1000, 995, 10)}, corner, offsets)
            self.assertEqual(late["tc"], late["to"])
            self.assertEqual(early["tc"], early["to"])

    def test_mixed_stub_cells_preserve_the_real_library(self):
        cells = {"s": dict(kind="stub", lib="BUFx2_ASAP7_75t_R"), "d": dict(kind="drv")}
        nets = [dict(name="root", drv="port:root", loads=["d"]),
                dict(name="ckm_w_s", drv="s", loads=["port:t_p__clk"])]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "clock.v"
            CM.write_verilog(cells, nets, [("output", "t_p__clk")], path)
            self.assertIn("BUFx2_ASAP7_75t_R s", path.read_text())
            self.assertIn(CM.BUF + " d", path.read_text())

    def test_regional_diagnostic_never_qualifies_missing_landings(self):
        M = dict(meta={"unplaced": 0}, unplaced=[])
        corners = {c: dict(verdict="PASS", landed_verdict="PASS") for c in ("TT", "FF")}
        self.assertEqual(CM.regional_qualification(M, corners, 3)["release_verdict"], "BLOCKED")
        self.assertEqual(CM.regional_qualification(M, corners, 0)["release_verdict"], "BLOCKED")
        self.assertTrue(any("related-pair coverage" in s for s in CM.regional_qualification(M, corners, 0)["blockers"]))
        M["unplaced"] = [[0, 0]]
        self.assertEqual(CM.regional_qualification(M, corners, 0)["release_verdict"], "BLOCKED")


LIBDIR = Path("~/.cache/opentallas/asap7_nldm").expanduser()


def _fp_plan(early=None):
    """3-partition floorplan fixture (same as test_floorplan_build_holes_prune_and_explicit_regions)."""
    types = dict(ta=dict(hard_cores=[dict(inst="core", origin_um=[400., 100.], outline_um=[250., 500.],
                                          obs_max="M5")]), tb={}, tc={})
    rects = dict(A=(0., 0., 700., 800.), B=(700., 0., 900., 600.), C=(900., 0., 1600., 800.),
                 PHY=(600., 600., 1000., 800.))
    P = SimpleNamespace(W=1600., H=800., clock={}, types=types, layer_budget=dict(partition_signal_max="M7"),
                        parts=dict(A=dict(type="ta"), B=dict(type="tb"), C=dict(type="tc")),
                        rect=lambda n: rects[n], to_die=lambda n, xy: xy)
    ko = [(400., 100., 650., 600., "A/core"), (600., 600., 1000., 800., "io/PHY")]
    fp = dict(x_cuts_um=[700., 900.], region_nx=[2, 1, 2], macro_holes=[dict(name="PHY", rect_um=list(rects["PHY"]))],
              hard_core_drivers="drop", shield_net="VSS")
    taps = [("A", "clk", 300., 300., 0.), ("A", "clk_c0", 120., 700., (early or {}).get("TT", 0.)),
            ("B", "clk", 790., 300., 0.), ("C", "clk", 1200., 300., 0.), ("C", "clk1", 1500., 50., 0.)]
    pte = {("A", "clk_c0"): early} if early else {}
    return P, ko, fp, taps, pte


def _build128(early=None, rule=True):
    P, ko, fp, taps, pte = _fp_plan(early)
    with patch.object(CM.DC, "keepouts", return_value=ko), patch.object(CM.DC, "plan_taps", return_value=taps), \
            patch.object(CM.DC, "plan_tap_early", return_value=pte), \
            patch("schema.core_taps", return_value=[("clk_c0", 0, 0, dict(budget_owner="core_lib_x"))]):
        return CM.build(P, 4, 4, m=1, max_move=50., region_edge_straps=True, floorplan=fp,
                        rule128=dict(libdir=str(LIBDIR)) if rule else None)


@unittest.skipUnless((LIBDIR / "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz").exists(), "ASAP7 NLDM liberty")
class Rule128(unittest.TestCase):
    """METHODOLOGY v4.1 12.8 items (1)-(4)."""

    def test_default_build_has_no_12_8_keys(self):
        cells, nets, ports, M = _build128(rule=False)
        self.assertNotIn("rule_12_8", M)
        self.assertNotIn("rule_12_8", M["meta"])
        self.assertFalse(M["meta"]["clock_shield"]["complete"])
        self.assertFalse(any("lib" in c for c in cells.values()))
        self.assertFalse(CM.C128.enabled(M))

    # (1) CPPR at the last common tree node only; mesh-node credit INFO only
    def test_gate_credits_region_root_not_mesh_node(self):
        M = dict(meta=dict(regions=[dict(k=0, tag="h0")]), drivers={},
                 taps=[dict(port="a", stub="sa", region=0), dict(port="b", stub="sb", region=0)])
        late, early = dict(a=1000., b=1060.), dict(a=940., b=1000.)
        rng = {"h": 5., "h0": 10.}                                   # region root range 10 ps
        mesh = dict(sa=dict(late=900., early=850.), sb=dict(late=950., early=900.))   # mesh-node range 50 ps
        g = CM.C128.gate(M, None, [("a", "b")], late, early, rng, 1, mesh, {}, [])
        # setup a late 1000 - b early 1000 = 0; hold b late 1060 - a early 940 = 120, minus credit 10 = 110
        self.assertAlmostEqual(g["related_pair_max_ps"], 110.0)
        self.assertAlmostEqual(g["info_mesh_node_cppr_max_ps"], 70.0)  # 120 - 50: INFO only, never the gate
        self.assertEqual(g["verdict"], "FAIL")
        # two regions: only the die root is common
        M["taps"][1]["region"] = 1
        M["meta"]["regions"].append(dict(k=1, tag="h1"))
        g = CM.C128.gate(M, None, [("a", "b", "seam-edge")], late, early, rng, 1, mesh, {}, [])
        self.assertAlmostEqual(g["related_pair_max_ps"], 115.0)

    # (2) early-offset taps: no add-back, gate FAIL naming the core type
    def test_early_offset_tap_fails_and_names_core(self):
        cells, nets, ports, M = _build128(early={"TT": 120., "FF": 95.})
        rows = M["rule_12_8"]["early_offset_taps"]
        self.assertEqual([(r["part"], r["tap"], r["core"]) for r in rows], [("A", "clk_c0", "core_lib_x")])
        self.assertIn("core_lib_x", M["rule_12_8"]["early_offset_cores"])
        self.assertEqual(M["meta"]["rule_12_8"]["early_offset_taps"], 1)
        tap = rows[0]["port"]
        other = next(t["port"] for t in M["taps"] if t["port"] != tap and t["region"] == 0)
        late = {tap: 500., other: 500.}
        early = {tap: 495., other: 495.}
        g = CM.C128.gate(M, None, [(tap, other)], late, early, {"h": 0.}, 1, {}, {}, rows)
        self.assertLessEqual(g["related_pair_max_ps"], 80.)        # skew itself fine (core already meets the target)...
        self.assertEqual(g["verdict"], "FAIL")                       # ...but a declared early offset is a FAIL
        self.assertIn("restructure", g["fails"][0])
        self.assertEqual(g["residual"]["core_latency"]["early_offset_taps"], 1)
        # no compensating branch: the core tap gets an ordinary stub like every tap
        stub = next(t["stub"] for t in M["taps"] if t["port"] == tap)
        self.assertEqual(cells[stub]["kind"], "stub")

    # (3) plan-model sizing, deterministic, no measured input; balance adds no cell and refuses measurements
    def test_stub_sizing_is_deterministic_plan_model(self):
        a = _build128()
        b = _build128()
        self.assertEqual(json.dumps(a[3]["rule_12_8"]["stub_sizing"], sort_keys=True),
                         json.dumps(b[3]["rule_12_8"]["stub_sizing"], sort_keys=True))
        cells, nets, ports, M = a
        for rk, r in M["rule_12_8"]["stub_sizing"]["regions"].items():
            self.assertLessEqual(r["model_spread_sized_ps"], r["model_spread_full_ps"] + 1e-9)
        libs = {t["stub_lib"] for t in M["taps"]}
        self.assertTrue(libs <= set(CM.C128.STUB_SIZES))
        for t in M["taps"]:
            self.assertEqual(cells[t["stub"]].get("lib", CM.BUF), t["stub_lib"])

    def test_balance_128_is_audit_only(self):
        cells, nets, ports, M = _build128()
        P, ko, fp, taps, pte = _fp_plan()
        with tempfile.TemporaryDirectory() as td:
            src, out = Path(td) / "b", Path(td) / "o"
            src.mkdir()
            ren = CM.write_verilog(cells, nets, ports, src / "ctree.v")
            M["meta"]["root_um"] = M["meta"].get("root_um", [800., 400.])
            (src / "mesh.json").write_text(json.dumps(M))
            (src / "place.json").write_text(json.dumps(cells))
            (src / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)))
            a = SimpleNamespace(dir=str(src), out=str(out), plan="unused", corner="TT", tree=None, tag="0",
                                libdir=str(LIBDIR))
            with patch.object(CM.S, "load", return_value={}), patch.object(CM.S, "Plan", return_value=P):
                self.assertEqual(CM.cmd_balance(a), 0)
                self.assertEqual(json.loads((out / "place.json").read_text()), cells)     # no pad, no swap
                au = json.loads((out / "balance_audit.json").read_text())
                self.assertIn("no measurement", au["method"])
                self.assertFalse((src / "tree_TT.txt").exists())
                a.tree = str(src / "tree_TT.txt")
                with self.assertRaises(SystemExit):
                    CM.cmd_balance(a)

    # (4) every tree net is a fixed, VSS-shielded pre-route with its own SPEF; shield record complete
    def test_tree_nets_fixed_shielded_and_spef(self):
        cells, nets, ports, M = _build128()
        sh = M["meta"]["clock_shield"]
        self.assertTrue(sh["complete"])
        self.assertEqual(sh["grt_routed_tree_nets"], 0)
        self.assertEqual(sh["fixed_tree_nets"], len(nets))
        wires = CM.C128.fixed_wires(M, cells, nets, CM.BUF_W, CM.ROW_Y)
        self.assertEqual({w["name"] for w in wires}, {n["name"] for n in nets})
        # never collinear with a mesh strap (the tree runs TREE_OFF_UM off every pin line)
        for w in wires:
            for lay, x0, y0, x1, y1 in w["segs"]:
                if lay == "M8":
                    self.assertTrue(all(abs(y0 - y) > 0.5 for y in M["ys"]) or x0 == x1)
                else:
                    self.assertTrue(all(abs(x0 - x) > 0.5 for x in M["xs"]) or y0 == y1)
        nd = CM.NDR["4w"]
        tcl = "\n".join(CM.C128.combo_tcl(wires, nd, "VSS"))
        self.assertEqual(tcl.count("[fwnet "), len(nets))
        self.assertIn("dbObstruction_create", tcl)
        self.assertEqual(tcl.count("\nfw $sw "), sh["fixed_tree_segs"])
        sp = CM.C128.spef(wires, cells, CM.BUF, nd, CM.DC.LAYER_RC, CM.DC.VIA_KOHM)
        import restore_clock_spef_caps as R
        from mix_clock_spef import header, sections
        import io
        f = io.StringIO(sp)
        h, names, first = header(f)
        n = 0
        for name, lines in sections(f, first, names):
            out, info = R.restore(lines, 4)
            self.assertEqual(info["added_caps"], 0)               # consistent caps: restore is a no-op
            n += 1
        self.assertEqual(n, len(nets))
        # Elmore length check on one stub: total C = wire length x C/um (NDR)
        w = next(w for w in wires if w["drv"].startswith("ckm_s_"))
        c_um = (CM.DC.LAYER_RC["M8"][1] if w["horiz"] else CM.DC.LAYER_RC["M9"][1]) * nd["cf"]
        tot = float(next(l for l in sp.split("\n") if l.startswith(f"*D_NET {w['name']} ")).split()[2])
        self.assertGreater(tot, 0.0)
        self.assertLessEqual(tot, w["wire_um"] * max(CM.DC.LAYER_RC["M8"][1], CM.DC.LAYER_RC["M9"][1]) * nd["cf"] + 1e-6)



class Rule128Export(unittest.TestCase):
    def test_tap_arrivals_export_for_die_sta(self):
        import tempfile, json as _j
        M = {"meta": {"regions": [dict(k=0, tag="h0"), dict(k=1, tag="h1")]},
             "taps": [dict(part="A", tap="clk", port="A__clk", region=0), dict(part="B", tap="clk_1", port="B__clk_1", region=1)]}
        arr = {"A__clk": (410.0, 395.5, 30.0), "B__clk_1": (420.25, 401.0, 31.0)}
        with tempfile.TemporaryDirectory() as td:
            out = CM.C128.write_tap_arrivals(Path(td) / "tap_arrivals_TT.json", M, "TT", arr,
                                             {"h": 5.0, "h0": 20.0, "h1": 21.0, "h00": 30.0}, 1)
            back = _j.loads((Path(td) / "tap_arrivals_TT.json").read_text())
        self.assertEqual(back["spine_late"], {"A": {"clk": 410.0}, "B": {"clk_1": 420.25}})
        self.assertEqual(back["spine_early"]["B"]["clk_1"], 401.0)
        self.assertEqual([r["cppr_node"] for r in out["taps"]], ["h0", "h1"])
        self.assertEqual(out["cppr_node_range_ps"], {"h": 5.0, "h0": 20.0, "h1": 21.0})   # tree nodes only

    def test_shield_record_not_vss_tied(self):
        r = CM.C128.shield_record([dict(wire_um=1000., segs=[1, 2])], "VSS", 4, 0)
        self.assertTrue(r["complete"])
        self.assertFalse(r["vss_tied"])
        self.assertFalse(r["freeze_evidence_ok"])

    def test_rule_12_8_is_the_default_build(self):
        seen = {}
        with patch.object(CM, "cmd_build", side_effect=lambda a: seen.update(r=a.rule_12_8) or 0):
            CM.main(["build", "plan.json", "--out", "o"])
            self.assertTrue(seen["r"])
            CM.main(["build", "plan.json", "--out", "o", "--legacy-pre-12-8"])
            self.assertFalse(seen["r"])


if __name__ == "__main__":
    unittest.main()


def test_stubtrim_pairs_complete_superset_and_damage():
    """stubtrim pair superset: all intra-partition tap pairs + tap cross-products of connected SAME-region partitions;
    connected cross-region partitions are landed (excluded); unconnected partitions never pair."""
    import types
    import die_clock_mesh as DM
    M = {"taps": [dict(port="a0", part="A", region=0), dict(port="a1", part="A", region=0),
                  dict(port="b0", part="B", region=0), dict(port="c0", part="C", region=1),
                  dict(port="d0", part="D", region=0)]}
    P = types.SimpleNamespace(ports={"p1": {"src": {"part": "A"}, "dst": {"part": "B"}},
                                     "p2": {"src": {"part": "B"}, "dst": {"part": "C"}}})
    pairs, reg = DM.stubtrim_pairs(P, M)
    assert pairs == [("a0", "a1"), ("a0", "b0"), ("a1", "b0")]
    arr = {"a0": (100.0, 40.0), "b0": (110.0, 50.0)}
    # late a0 vs early b0 and late b0 vs early a0 (70), minus the region-node credit 30
    assert DM.pair_damage(arr, {0: 30.0}, reg, "a0", "b0") == 40.0
    # lifting b0 by 10 (early side 0.97 x) raises the damage by 10 + 0.3
    assert abs(DM.pair_damage(arr, {0: 30.0}, reg, "a0", "b0", {"b0": 10.0}, 0.97) - 50.0) < 1e-9


def test_kv_site_fixes_default_off():
    import inspect
    import die_clock_mesh as DM
    sig = inspect.signature(DM.build)
    assert sig.parameters["trunk_repeaters"].default is False
    assert sig.parameters["driver_pair_span_um"].default == 0.0
    assert sig.parameters["split_yfirst"].default is False
    assert inspect.signature(DM.split_long).parameters["yfirst"].default is False


def test_report_12_8d_banned_means_never_pass():
    import die_clock_mesh as DM
    clean = dict(meta={}, taps=[dict(port="a", early_ps=0.0)])
    assert DM.banned_means_12_8d(clean) == []
    rep = dict(corners={"TT": dict(verdict="PASS", landed_verdict="PASS"), "FF": dict(verdict="PASS")})
    assert DM.apply_12_8d(rep, []) is None and rep["corners"]["TT"]["verdict"] == "PASS"
    for meta, taps in [(dict(stubtrim=dict(pads=3)), []), (dict(balance=dict(pads=2)), []),
                       ({}, [dict(port="a", early_ps=-40.0)])]:
        M = dict(meta=meta, taps=taps)
        why = DM.banned_means_12_8d(M)
        assert why
        rep = dict(corners={"TT": dict(verdict="PASS", landed_verdict="PASS"), "FF": dict(verdict="PASS")})
        b = DM.apply_12_8d(rep, why)
        assert b.startswith("built with 12.8d banned means")
        assert all(r["verdict"] == DM.INFO_128D for r in rep["corners"].values())
        assert rep["corners"]["TT"]["landed_verdict"] == DM.INFO_128D
        assert rep["corners"]["TT"]["verdict_measured"] == "PASS"
        q = DM.regional_qualification(dict(meta={}), rep["corners"], 0)
        assert q["release_verdict"] == "BLOCKED"


def test_rule128_requires_explicit_budget_and_liberty(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path
    import die_clock_mesh as DM
    fixture = Path(DM.__file__).parent / "examples/tiny_plan.json"
    raw = json.loads(fixture.read_text())
    raw["die"].pop("layer_budget", None)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(raw))
    out = tmp_path / "out"
    cmd = [sys.executable, DM.__file__, "build", str(plan), "--out", str(out),
           "--rule-12-8", "--libdir", str(tmp_path / "missing_libs")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode and "explicit die.layer_budget" in r.stderr
    assert "Traceback" not in r.stderr and not out.exists()
    raw["die"]["layer_budget"] = {"partition_signal_max": "M7", "die_layers": ["M8", "M9"]}
    plan.write_text(json.dumps(raw))
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode and "missing ASAP7 TT liberty" in r.stderr
    assert "Traceback" not in r.stderr and not out.exists()
