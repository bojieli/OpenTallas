"""MASTER-PLAN-R6: regional tree_commensurate gate + hub re-pack mode (hub_repack.py)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hub_repack as HR  # noqa: E402
import master_plan as MP  # noqa: E402


class _P:
    """minimal plan stand-in for regional_tree_commensurate."""

    def __init__(self, parts, regions=None):
        self.parts = {k: dict(type=f"t_{k}") for k in parts}
        self._r = parts
        self.clock = dict(regions=regions) if regions else {}
        self.lanes = {"L0": {}}

    def rect(self, p):
        return self._r[p]

    def lane_crossings(self, lid):
        return [("A", "s", None, None), ("B", "s", None, None)]


def _grid(part, mod, x0, y0, nx, ny, px, py):
    return [(part, f"{mod}{i}_{j}", mod, (x0 + i * px, y0 + j * py)) for i in range(nx) for j in range(ny)]


def test_regional_pass_regular_array_and_commensurate_tree():
    P = _P({"A": (0, 0, 2000, 2000), "B": (2000, 0, 4000, 2000)})
    rows = _grid("A", "m", 100, 100, 4, 4, 259.2, 259.2) + _grid("B", "n", 2100, 100, 3, 3, 345.6, 345.6)
    # tree points in A at half-repeat multiples (129.6 phase), one point in B
    tree = [("a0", (229.6, 229.6)), ("a1", (229.6 + 2 * 129.6, 229.6)), ("b0", (2500.0, 500.0))]
    g = MP.regional_tree_commensurate(P, rows, tree)
    assert g["verdict"] == "PASS", g
    assert g["regions"] == 2 and g["regions_with_tree_points"] == 2 and g["inter_region_lanes"] == 1


def test_regional_fails_irregular_type_and_off_phase_tree():
    P = _P({"A": (0, 0, 2000, 2000)})
    rows = [("A", f"c{i}", "m", (x, 100.0)) for i, x in enumerate((100.0, 151.84, 380.16, 1001.12, 1400.0))]
    g = MP.regional_tree_commensurate(P, rows, [])               # fed from one point: INFO only
    assert g["verdict"] == "PASS" and g["regions_irregular_islands"] == 1
    g = MP.regional_tree_commensurate(P, rows, [("t0", (100.0, 50.0)), ("t1", (700.0, 50.0))])
    assert g["verdict"] == "FAIL" and g["fail_examples"][0]["axes"]["x"]["n_irregular_types"] == 1
    rows = _grid("A", "m", 100, 100, 4, 1, 259.2, 1)
    g = MP.regional_tree_commensurate(P, rows, [("t0", (100.0, 50.0)), ("t1", (100.0 + 77.0, 50.0))])
    assert g["verdict"] == "FAIL" and not g["rows"][0]["axes"]["x"]["tree_coincides"]


def test_regional_declared_regions_join_partitions():
    P = _P({"A": (0, 0, 1000, 1000), "B": (1000, 0, 2000, 1000)}, regions=[dict(name="R", parts=["A", "B"])])
    rows = _grid("A", "m", 100, 100, 2, 1, 518.4, 1) + _grid("B", "m", 1136.8, 100, 2, 1, 518.4, 1)
    g = MP.regional_tree_commensurate(P, rows, [("t0", (359.2, 500.0)), ("t1", (1395.99, 500.0))])
    assert g["regions"] == 1 and g["regions_from"] == "declared clock.regions"
    assert g["verdict"] == "PASS", g["rows"]
    assert g["inter_region_lanes"] == 0


def test_tree_commensurate_flag_default_is_die_form():
    import argparse
    ap = argparse.ArgumentParser()
    MP.add_args(ap)
    a = ap.parse_args(["plan.json", "--out", "x"])
    assert a.tree_commensurate == "die"


# ------------------------------------------------------------------------------------------------ hub re-pack
def test_shrink_decision_rules():
    assert HR.shrink_decision(dict(macro_fit=True, est_fill=0.55))[0]
    assert not HR.shrink_decision(dict(macro_fit=True, est_fill=0.66))[0]       # bfqg: fill > 0.6
    assert not HR.shrink_decision(dict(macro_fit=False, est_fill=0.4))[0]       # sfustore_hw / hfd_ep_static


def test_remap_pins_keeps_edges_order_and_pitch():
    pins = [dict(name=f"s{i}", layer="M5", x=2.0 + 0.288 * i, y=0.019) for i in range(50)]
    pins += [dict(name="n0", layer="M5", x=150.0, y=280.78), dict(name="e0", layer="M4", x=302.38, y=100.0)]
    out = HR.remap_pins(pins, (302.4, 280.8), (224.64, 207.36))
    s = [p for p in out if p["name"].startswith("s")]
    assert all(p["y"] == 0.019 for p in s)
    xs = [p["x"] for p in s]
    assert xs == sorted(xs) and min(b - a for a, b in zip(xs, xs[1:])) >= 0.192 - 1e-6
    n0 = next(p for p in out if p["name"] == "n0")
    e0 = next(p for p in out if p["name"] == "e0")
    assert abs(n0["y"] - (207.36 - 0.02)) < 1e-6 and abs(e0["x"] - (224.64 - 0.02)) < 1e-6


def test_pack_hub_regular_lattice_no_overlap():
    cores = [dict(inst=f"c{i}", w=w, h=h, ocx=100 + 300 * (i % 6), ocy=100 + 400 * (i // 6))
             for i, (w, h) in enumerate([(200, 300), (120, 120), (250, 250), (90, 400), (300, 200), (150, 150)] * 3)]
    place, info = HR.pack_hub(2400.0, 1600.0, cores)
    rects = []
    for c in cores:
        x, y = place[c["inst"]]
        assert abs(x / HR.G - round(x / HR.G)) < 1e-6 and abs(y / HR.G - round(y / HR.G)) < 1e-6
        rects.append((x, y, x + c["w"], y + c["h"]))
        assert 0 <= x and x + c["w"] <= 2400.0 and 0 <= y and y + c["h"] <= 1600.0
    lane = info["lane_um"]
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            gx = max(b[0] - a[2], a[0] - b[2])
            gy = max(b[1] - a[3], a[1] - b[3])
            assert max(gx, gy) >= lane - 1e-6          # every pair separated by at least one street


def test_route_station_registers_in_streets_and_reach():
    rects = [(100.0, 100.0, 700.0, 300.0)]                 # one core; pins on its S and N edges
    R = HR.Raster(1200.0, 800.0, rects)
    res = HR.route_station(R, (400.0, 100.0), (1100.0, 700.0), n_old=3, reach=360.0, streets_y=[400.0])
    assert res is not None and len(res["regs"]) >= 3
    assert all(R.free(*r) for r in res["regs"])
    pts = [(400.0, 100.0)] + [tuple(r) for r in res["regs"]] + [(1100.0, 700.0)]
    # hops measured along the Manhattan route are <= reach, so the straight distance is too
    assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) <= 360.0 + 1e-6 for a, b in zip(pts, pts[1:]))


def test_run_bundle_end_to_end(tmp_path):
    hub = dict(outline_um=[1728.0, 864.0], hard_cores=[
        dict(inst="u_a", module="ma", origin_um=[86.4, 86.4], outline_um=[302.4, 280.8], pins_file="cores/ma__302.4x280.8__h_u_a.json"),
        dict(inst="u_b", module="mb", origin_um=[1000.0, 400.0], outline_um=[200.0, 200.0])],
        contents=[dict(inst="u_a", origin_um=[86.4, 86.4], outline_um=[302.4, 280.8])],
        clock=dict(tap_um=[800.0, 400.0], taps=[dict(name="u_a", xy=[237.6, 220.32])]), reset=dict(tap_um=[800.0, 400.0]),
        internal_stations=[dict(conn="bus:X", from_um=[0.0, 430.0], to_um=[237.6, 86.4], regs_um=[[50.0, 430.0]], bits=8),
                           dict(conn="u_a.o|u_b", from_um=[389.0, 200.0], to_um=[1000.0, 500.0], regs_um=[[600.0, 200.0], [800.0, 200.0]], bits=4)])
    P = dict(partition_types=dict(h=hub, other=dict(outline_um=[100, 100], hard_cores=[])), note="")
    d = tmp_path / "plan"
    (d / "cores").mkdir(parents=True)
    (d / "die_plan.json").write_text(json.dumps(P))
    (d / "entries.json").write_text(json.dumps(dict(ma=dict(xy=[151.2, 138.24]))))
    (d / "cores/ma__302.4x280.8__h_u_a.json").write_text(json.dumps([dict(name="p0", layer="M5", x=151.2, y=0.019)]))
    spec = [dict(module="ma", outline_um=[224.64, 207.36], est_fill=0.55, macro_fit=True)]
    rep = HR.run(d, tmp_path / "out", ["h"], spec, log=lambda *a: None)
    Q = json.loads((tmp_path / "out/die_plan.json").read_text())
    t = Q["partition_types"]["h"]
    a = next(h for h in t["hard_cores"] if h["inst"] == "u_a")
    assert a["outline_um"] == [224.64, 207.36] and (tmp_path / "out" / a["pins_file"]).exists()
    E = json.loads((tmp_path / "out/entries.json").read_text())
    assert E["ma"]["xy"] == [112.32, 103.68]
    assert rep["stations"]["h"]["regenerated"] == 2 and not rep["stations"]["h"]["failed"]
    rects = [HR._core_rect(h) for h in t["hard_cores"]]
    for st in t["internal_stations"]:
        assert len(st["regs_um"]) >= 1
        for x, y in st["regs_um"]:
            assert not any(r[0] - 4.32 < x < r[2] + 4.32 and r[1] - 4.32 < y < r[3] + 4.32 for r in rects)
    # the input bundle is untouched
    assert json.loads((d / "die_plan.json").read_text()) == P
