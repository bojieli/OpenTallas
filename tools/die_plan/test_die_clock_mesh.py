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
