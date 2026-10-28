"""HBM-STREETS-1 (OWNER 10-27 ~18:4x, METHODOLOGY 12.10c): G0C street rule (streets.py, check.check_streets)."""
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import streets as ST  # noqa: E402

CFG = ST.config()          # width 34.56 um = ceil((4.32 + 4.32 + 8.64) / 0.6 / 8.64) * 8.64


def _row(n, w=300.0, h=300.0, gap=69.12, x0=69.12, y0=69.12):
    return [(x0 + k * (w + gap), y0, x0 + k * (w + gap) + w, y0 + h, f"c{k}") for k in range(n)]


def test_required_width():
    assert abs(CFG["required_width_um"] - 34.56) < 1e-9
    assert abs(ST.config(dict(ft_um=17.28))["required_width_um"] - 43.2) < 1e-9


def test_cores_on_street_grid_pass():
    A = ST.analyze(2000.0, 500.0, _row(4), CFG)
    assert not A["errors"], A["errors"]
    assert max(c["street_dist_um"] for c in A["cores"]) <= 160.0          # half the 300-um core + raster


def test_big_core_far_from_street_fails():
    ko = [(17.28, 17.28, 1017.28, 1017.28, "big")]                      # 1000 x 1000 core: centre ~500 um from streets
    A = ST.analyze(1100.0, 1100.0, ko, CFG)
    assert [e[0] for e in A["errors"]] == ["street_reach"] and "big" in A["errors"][0][2]


def test_narrow_slit_is_not_a_street():
    # two 370-um cores filling the die but a 17.28-um slit (< 34.56 street width): the slit is no street
    ko = [(0.0, 0.0, 370.0, 2000.0, "a"), (387.28, 0.0, 757.28, 2000.0, "b")]
    A = ST.analyze(757.28, 2000.0, ko, CFG)
    assert {e[1] for e in A["errors"] if e[0] == "street_reach"} == {"a", "b"}
    assert "no street" in A["errors"][0][2]
    ko2 = [(0.0, 0.0, 370.0, 2000.0, "a"), (413.2, 0.0, 783.2, 2000.0, "b")]    # 43.2-um street: both within reach
    A2 = ST.analyze(783.2, 2000.0, ko2, CFG)
    assert not [e for e in A2["errors"] if e[0] == "street_reach"]


def test_enclosed_pocket_is_not_a_street():
    # a ring of cores around a 200x200 pocket: the pocket is a separate component, not part of the street network
    ring = [(100, 100, 900, 300, "s"), (100, 500, 900, 700, "n"), (100, 300, 300, 500, "w"), (700, 300, 900, 500, "e")]
    A = ST.analyze(1000.0, 800.0, ring, CFG)
    assert A["streets"]["pockets"] == 1 and A["streets"]["pocket_area_mm2"] > 0


def test_declared_width_below_budget_fails():
    A = ST.analyze(2000.0, 500.0, _row(4), ST.config(dict(width_um=17.28)))
    assert [e[0] for e in A["errors"]] == ["street_width"]


def test_clock_leg_across_core_fails_along_street_passes():
    ko = _row(2)                                                            # c0 x 69..369, c1 x 438..738, y 69..369
    over = ST.analyze(900.0, 500.0, ko, CFG, legs=[("L9:h0", (20.0, 200.0), (800.0, 200.0))])
    assert [e[0] for e in over["errors"]] == ["street_clock_leg"] and over["legs_over_core"][0]["core"] == "c0"
    street = ST.analyze(900.0, 500.0, ko, CFG, legs=[("L9:h1", (20.0, 420.0), (800.0, 420.0)),
                                                     ("L10:h2", (403.68, 20.0), (403.68, 480.0))])
    assert not street["errors"]
    edge = ST.analyze(900.0, 500.0, ko, CFG, legs=[("L9:e", (20.0, 369.12), (800.0, 369.12))])   # along core edges
    assert not edge["errors"]
    lpath = ST.analyze(900.0, 500.0, ko, CFG, legs=[("L9:l", (20.0, 200.0), (403.68, 420.0))])  # x first -> crosses c0
    assert lpath["legs_over_core"]


def test_points_and_unplaced():
    A = ST.analyze(900.0, 500.0, _row(2), CFG, points=[("ckm_d_1_1", (200.0, 200.0), "clock_driver"),
                                                       ("L1#1", (403.68, 200.0), "lane_station"),
                                                       ("L2#1", (500.0, 200.0), "lane_station")],
                   unplaced=[("ckm_n8:ckm_n9", "STRUCTURAL clock span exceeds 480 um")])
    assert sorted(e[0] for e in A["errors"]) == ["street_clock_leg", "street_clock_leg", "street_die_leg"]


class _P:
    """minimal plan stand-in for check.check_streets (die_clock.keepouts reads parts/types/to_die/die.io)."""
    def __init__(self, cores, W=2000.0, H=500.0, streets=None, name="hbm_t"):
        self.W, self.H, self.name = W, H, name
        self.die = dict(io=[], **({"streets": streets} if streets else {}))
        self.types = dict(t=dict(hard_cores=[dict(inst=n, origin_um=[r[0], r[1]], outline_um=[r[2] - r[0], r[3] - r[1]])
                                             for *r, n in cores]))
        self.parts = dict(p0=dict(type="t", origin_um=[0.0, 0.0], orient="R0"))

    def ptype(self, n):
        return self.types[self.parts[n]["type"]]

    def to_die(self, n, pt):
        return pt


def test_check_streets_g0c_levels(tmp_path):
    P = _P([(17.28, 17.28, 1017.28, 482.72, "big")], W=1100.0, H=500.0, streets=dict(reach_um=200.0))
    R = check.Report(True)
    out = check.check_streets(P, R)
    assert out["cores_over_reach"] == 1 and any(i["check"] == "street_reach" for i in R.errors())
    R2 = check.Report(False)
    check.check_streets(P, R2)
    assert not R2.errors() and any(i["msg"].startswith("[G0C]") for i in R2.items)
    for c in ("street_reach", "street_width", "street_clock_leg", "street_die_leg"):
        assert c in check.G0C_CHECKS


def test_clock_build_rows(tmp_path):
    d = tmp_path / "mesh"
    d.mkdir()
    (d / "plan_errors.json").write_text(json.dumps(dict(rows=[
        dict(kind="unplaced", name="n8:n9", role="tree", detail=["n8", "n9", "STRUCTURAL clock span exceeds 480 um", 640.0]),
        dict(kind="shield_tie", name="w", detail="x")])))
    (d / "mesh.json").write_text(json.dumps(dict(htree=[dict(level=9, tag="h0", a=[20.0, 200.0], b=[800.0, 200.0])],
                                                 drivers={"0_0": dict(site=[100.0, 100.0])}, unplaced=[[1, 11]])))
    legs, pts, unpl = ST.clock_build_legs(tmp_path)
    assert len(legs) == 1 and len(pts) == 1 and len(unpl) == 2


def test_phy_macro_is_obstacle_not_core():
    ko = [(0.0, 0.0, 2000.0, 1000.0, "io/io_PHY_N"), (0.0, 1100.0, 300.0, 1400.0, "c0"),
          (1000.0, 1100.0, 2000.0, 1500.0, "NW_io/clock_keepout_0")]
    A = ST.analyze(2000.0, 1500.0, ko, CFG)
    assert not A["errors"] and [c["name"] for c in A["cores"]] == ["c0"]


def test_render(tmp_path):
    import pytest
    pytest.importorskip("matplotlib")
    ko = _row(2)
    A = ST.analyze(900.0, 500.0, ko, CFG, legs=[("L9:h0", (20.0, 200.0), (800.0, 200.0))])
    ST.render(A, ko, tmp_path / "s.png", 900.0, 500.0, "t")
    assert (tmp_path / "s.png").stat().st_size > 1000


def test_severity_hbm_error_other_dies_report_only():
    # COORD 10-27 18:52: ERROR on hbm, REPORT-ONLY (WARN) on the other dies; die.streets.enforce overrides
    cores = [(17.28, 17.28, 1017.28, 482.72, "big")]
    for name, streets, want in (("hbm_arch_B2o", dict(reach_um=200.0), True), ("s81", dict(reach_um=200.0), False),
                                ("s81", dict(reach_um=200.0, enforce=True), True)):
        R = check.Report(True)
        out = check.check_streets(_P(cores, W=1100.0, H=500.0, streets=streets, name=name), R)
        assert out["enforce"] is want and bool(R.errors()) is want
        assert any(i["check"] == "street_reach" for i in R.items)


def test_per_street_demand_base_and_ft():
    # HBM-STREETS-2: per-street demand. A 17.28-um slit carrying no FT is a street (base (4.32 + 4.32) / 0.6 -> 17.28);
    # the same slit carrying a 1000-bit N-S flow needs 17.28 + 1000 x 0.04 = 57.28 um and is no street.
    assert abs(ST.base_width(CFG) - 17.28) < 1e-9 and abs(ST.ft_um_per_bit(CFG) - 0.04) < 1e-9
    ko = [(0.0, 0.0, 370.0, 2000.0, "a"), (387.28, 0.0, 757.28, 2000.0, "b")]
    A = ST.analyze(757.28, 2000.0, ko, CFG, flows=[])
    assert not A["errors"] and A["streets"]["demand"]["base_um"] == 17.28
    A2 = ST.analyze(757.28, 2000.0, ko, CFG, flows=[("L1", 1000, [(378.0, 0.0), (378.0, 2000.0)])])
    assert {e[1] for e in A2["errors"] if e[0] == "street_reach"} == {"a", "b"}
    assert abs(A2["streets"]["demand"]["max_req_ns_um"] - 57.28) < 1e-6
    ko3 = [(0.0, 0.0, 370.0, 2000.0, "a"), (439.12, 0.0, 809.12, 2000.0, "b")]          # 69.12-um street >= 57.28
    A3 = ST.analyze(809.12, 2000.0, ko3, CFG, flows=[("L1", 1000, [(400.0, 0.0), (400.0, 2000.0)])])
    assert not A3["errors"]


def test_phy_hard_core_inside_io_rect_not_reach_checked():
    ko = [(0.0, 0.0, 600.0, 1050.0, "io/io_x"), (4.0, 0.0, 604.0, 600.0, "NW_io/u_lk_N0"), (0.0, 1100.0, 300.0, 1400.0, "c0")]
    A = ST.analyze(2000.0, 1500.0, ko, CFG, flows=[])
    assert [c["name"] for c in A["cores"]] == ["c0"]
