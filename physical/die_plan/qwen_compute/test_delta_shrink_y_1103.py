"""Tests for delta_shrink_y_1103 (DIE-QC-66/PLAN QC y-shrink)."""
import copy, json, os, sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import delta_shrink_y_1103 as ds  # noqa: E402

POR = os.path.join(HERE, "plan_of_record", "plan_qc52.json")
R = ds.r6


def _core(x, y):
    return {"inst": "u", "module": "m", "origin_um": [x, y], "outline_um": [457.92, 1157.76], "orient": "R0"}


def _cb():
    return {"outline_um": [1235.52, 2609.28],
            "buses": [{"name": "e", "face": "E", "window_um": [1500.0, 1600.0]},
                      {"name": "n", "face": "N", "window_um": [1400.0, 1450.0]}],
            "hard_cores": [_core(86.4, 77.76), _core(86.4, 1382.4)],
            "clock": {"tap_um": [622.08, 1313.28], "landing_contract": {"collector_tree": {"relays": [
                {"name": "r0", "xy": [300.0, 1334.3]}, {"name": "r1", "xy": [300.0, 1378.08]},
                {"name": "r2", "xy": [622.0, 1334.3]}]}}}}


def test_cb_type_shift():
    t, st = _cb(), ds.new_stats()
    ds.shift_cb_type(t, st)
    assert t["outline_um"] == [1235.52, R(2609.28 - ds.D)]
    assert t["hard_cores"][1]["origin_um"][1] == R(1382.4 - ds.D) and t["hard_cores"][0]["origin_um"][1] == 77.76
    assert t["buses"][0]["window_um"] == [R(1500 - ds.D), R(1600 - ds.D)]
    assert t["buses"][1]["window_um"] == [1400.0, 1450.0]          # N face: x window untouched
    assert t["clock"]["tap_um"] == [622.08, 1313.28]
    rl = {r["name"]: r["xy"] for r in t["clock"]["landing_contract"]["collector_tree"]["relays"]}
    assert rl["r0"] == [300.0, R(1382.4 - ds.D - ds.CORE_CLEAR)]   # was left inside the moved core
    assert rl["r1"] == [300.0, R(1378.08 - ds.D)]
    assert rl["r2"] == [622.0, 1334.3]                             # centre column: free, stays


def test_west_cut_type():
    t = {"outline_um": [786.24, 993.6], "buses": [{"name": "w", "face": "W", "window_um": [850.0, 900.0]},
                                                  {"name": "s", "face": "S", "window_um": [10.0, 20.0]}],
         "reset": {"tap_um": [393.0, 500.0]}, "x": [[1.0, 830.0]]}
    ds.cut_type(t, 820.0, 207.36, ds.new_stats())
    assert t["outline_um"] == [786.24, R(993.6 - 207.36)]
    assert t["buses"][0]["window_um"] == [R(850 - 207.36), R(900 - 207.36)] and t["buses"][1]["window_um"] == [10.0, 20.0]
    assert t["reset"]["tap_um"] == [393.0, 500.0] and t["x"] == [[1.0, R(830 - 207.36)]]


def _seam():
    t = _cb()
    t["outline_um"] = [1235.52, 2531.52]
    t["hard_cores"][1]["origin_um"] = [86.4, 1304.64]
    regs = [[0.0, 382.75], [77.76, 328.32], [77.76, 648.0], [77.76, 967.68], [77.76, 1287.36], [77.76, 1529.28]]
    t["ft_slots"] = [{"name": "a", "in_face": "W", "out_face": "N", "regs_um": copy.deepcopy(regs),
                      "bit_sites_um": [[[60.0, r[1]], [70.0, r[1] + 1.0]] for r in regs[1:]]},
                     {"name": "b", "in_face": "N", "out_face": "W", "out_window_um": [449.6, 574.56],
                      "regs_um": [[200.0, 2531.52], [77.76, 1425.6], [77.76, 1183.68], [77.76, 864.0], [34.56, 587.52]],
                      "bit_sites_um": [[[60.0, y]] for y in (1425.6, 1183.68, 864.0, 587.52)]},
                     {"name": "c", "in_face": "N", "out_face": "S", "regs_um": [[1.0, 2.0], [3.0, 4.0]], "bit_sites_um": [[[3.0, 4.0]]]}]
    lc = t["clock"]["landing_contract"]
    lc["pins"] = [{"name": "fclk_in_a_i", "xy_um": [2.144, 382.94]}, {"name": "fclk_in_n", "xy_um": [236.0, 2528.86]}]
    lc["bands"] = {"a_i": {"rect_um": [17.28, 365.0, 56.16, 494.0]}, "b_i": {"rect_um": [98.9, 2486.0, 388.0, 2503.0]}}
    lc["collector_local_sources"] = [{"name": "a_i", "xy_um": [0, 383.0], "pin_xy_um": [0, 383.0], "band": {"rect_um": [17.28, 318.0, 41.0, 447.0]}}]
    t["clock"]["edge_clocks"] = [{"port": "fclk_in_a_i", "tap_um": [2.144, 382.94]}]
    return t


def test_w_seam_resite():
    t, st = _seam(), ds.new_stats()
    ds.resite_w_seam(t, ds.SEAM_DY, st)
    a, b, c = t["ft_slots"]
    dy = ds.SEAM_DY
    assert a["regs_um"][0] == [0.0, R(382.75 + dy)] and a["regs_um"][1] == [77.76, R(328.32 + dy)]
    assert b["out_window_um"] == [R(449.6 + dy), R(574.56 + dy)] and b["regs_um"][4] == [34.56, R(587.52 + dy)]
    assert a["regs_um"][4:] == [[77.76, 1287.36], [77.76, 1529.28]] and b["regs_um"][:2] == [[200.0, 2531.52], [77.76, 1425.6]]
    assert c["regs_um"] == [[1.0, 2.0], [3.0, 4.0]]
    for s in (a, b):                       # hops <= reach, monotone, on grid, bit sites rigid with their station
        rs = sorted(s["regs_um"][1:], key=lambda r: r[1])
        assert all(0 < q[1] - p[1] and abs(q[0] - p[0]) + q[1] - p[1] <= 405 for p, q in zip(rs, rs[1:]))
        for r, g in zip(s["regs_um"][1:], s["bit_sites_um"]):
            assert g[0][1] == pytest.approx(r[1])
    assert a["regs_um"][2][1] % ds.GRID == pytest.approx(0, abs=1e-6) or a["regs_um"][2][1] % ds.GRID == pytest.approx(ds.GRID)
    lc = t["clock"]["landing_contract"]
    assert lc["pins"][0]["xy_um"] == [2.144, R(382.94 + dy)] and lc["pins"][1]["xy_um"] == [236.0, 2528.86]
    assert lc["bands"]["a_i"]["rect_um"] == [17.28, R(365 + dy), 56.16, R(494 + dy)]
    assert lc["bands"]["b_i"]["rect_um"] == [98.9, 2486.0, 388.0, 2503.0]
    assert lc["collector_local_sources"][0]["xy_um"] == [0, R(383 + dy)]
    assert t["clock"]["edge_clocks"][0]["tap_um"] == [2.144, R(382.94 + dy)]
    assert st["stations_respaced"] == 6 and st["seam_items"] == 4


def test_west_dy():
    cuts = [(6271.84, 207.36), (6745.44, 51.84), (7739.04, 51.84)]
    assert ds.west_dy(777.6, 5451.84, cuts) == 0                      # coll_f0 stays
    assert ds.west_dy(777.6, 6445.44, cuts) == pytest.approx(-207.36)  # coll_f1
    assert ds.west_dy(777.6, 7439.04, cuts) == pytest.approx(-259.2)   # coll_f2
    assert ds.west_dy(777.6, 8432.64, cuts) == pytest.approx(-4 * ds.D)
    assert ds.west_dy(0.0, 7603.2, cuts) == pytest.approx(-4 * ds.D)   # coll_ucie (edge column)
    assert ds.west_dy(0.0, 2324.16, cuts) == 0                        # io_serdes_1


def test_refuses_second_apply():
    p = {"die": {"outline_um": [31216.32, ds.NEW_H]}}
    with pytest.raises(SystemExit):
        ds.apply(p)


@pytest.mark.skipif(not os.path.exists(POR), reason="plan_of_record not checked out")
def test_plan_of_record_shrunk():
    p = json.load(open(POR))
    W, H = p["die"]["outline_um"]
    assert H <= 25690.0 and H == pytest.approx(ds.NEW_H)
    T = p["partition_types"]
    rects = {}
    for q in p["partitions"]:
        x, y = q["origin_um"]; w, h = T[q["type"]]["outline_um"]
        assert x >= -1e-6 and y >= -1e-6 and x + w <= W + 1e-6 and y + h <= H + 1e-6, q["name"]
        rects[q["name"]] = (x, y, x + w, y + h)
    by_x = sorted(rects, key=lambda n: rects[n][0])
    for i, a in enumerate(by_x):          # no partition overlap
        ax0, ay0, ax1, ay1 = rects[a]
        for b in by_x[i + 1:]:
            bx0, by0, bx1, by1 = rects[b]
            if bx0 >= ax1 - 1e-6:
                break
            assert not (min(ax1, bx1) - max(ax0, bx0) > 1e-6 and min(ay1, by1) - max(ay0, by0) > 1e-6), (a, b)
    for n, t in T.items():                # every cb core inside its type, every relay outside the cores
        if not n.startswith("cb"):
            continue
        cores = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                  c["origin_um"][1] + c["outline_um"][1]) for c in t["hard_cores"]]
        assert all(c[3] <= t["outline_um"][1] + 1e-6 for c in cores), n
        for i, a in enumerate(cores):
            assert not any(min(a[2], b[2]) > max(a[0], b[0]) + 1e-6 and min(a[3], b[3]) > max(a[1], b[1]) + 1e-6
                           for b in cores[i + 1:]), n
        for r in t["clock"]["landing_contract"]["collector_tree"]["relays"]:
            x, y = r["xy"]
            assert not any(x0 + 1e-6 < x < x1 - 1e-6 and y0 + 1e-6 < y < y1 - 1e-6 for x0, y0, x1, y1 in cores), (n, r["name"])
