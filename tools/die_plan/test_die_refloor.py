"""die_refloor.py (DIE-REFLOOR, DIE-S81-89 11-13): re-place partitions after type growth, pad on the type-high side,
re-derive die ports, report conflicts / reticle."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_refloor as D  # noqa: E402


def T(w, h, buses):
    return {"outline_um": [w, h], "buses": [dict(name=n, dir=d, width=4, kind="data", face=f, window_um=list(win),
                                                 layers=["M7", "M5"]) for n, d, f, win in buses]}


def P(name, tn, x, y, orient="R0"):
    return {"name": name, "type": tn, "origin_um": [x, y], "orient": orient}


def port(pid, a, ab, b, bb):
    return {"id": pid, "src": {"part": a, "bus": ab}, "dst": {"part": b, "bus": bb}, "width": 4, "kind": "data"}


def plan(types, parts, ports, W, H, channels=()):
    raw = {"die": {"outline_um": [W, H], "channels": list(channels)}, "partition_types": types, "partitions": parts,
           "ports": ports, "lanes": []}
    geo = D.Geo(raw)
    for q in ports:                       # write the die-frame port geometry from the src type (as a plan does)
        g = geo.port_geoms(q)[0]
        q["face"], q["window_um"], q["layers"] = g[0], list(g[1]), ["M7", "M5"]
    assert D.plan_check(raw) == [], D.plan_check(raw)
    return raw


def column():
    """two partitions stacked: lo (0,0 100x100) N-port -> hi (0,100)."""
    types = {"lo": T(100, 100, [("o", "out", "N", (10, 20))]), "hi": T(100, 100, [("i", "in", "S", (10, 20))])}
    return plan(types, [P("a", "lo", 10, 10), P("b", "hi", 10, 110)], [port("p", "a", "o", "b", "i")], 120, 220)


def test_base_is_fixed_point():
    raw = column()
    Q, rep = D.refloor(raw, copy.deepcopy(raw), log=lambda *a: None)
    assert rep["conflicts"] == [] and rep["moved_partitions"] == 0 and rep["dH"] == 0 and D.plan_check(Q) == []


def test_growth_pushes_neighbour_and_die():
    raw = column()
    cand = copy.deepcopy(raw)
    cand["partition_types"]["lo"]["outline_um"] = [100, 130]
    Q, rep = D.refloor(raw, cand, log=lambda *a: None)
    parts = {p["name"]: p for p in Q["partitions"]}
    assert parts["b"]["origin_um"] == [10, 140]
    assert Q["die"]["outline_um"] == [120, 250] and rep["dH"] == 30
    assert D.plan_check(Q) == [] and rep["conflicts"] == []


def row_with_tops(orient_right="R0"):
    """a | c side by side tied by an E/W port; b on a, d on c (N/S ports)."""
    types = {
        "A": T(100, 100, [("o", "out", "N", (10, 20)), ("e", "out", "E", (30, 40))]),
        "B": T(100, 100, [("i", "in", "S", (10, 20)), ("e", "out", "E", (60, 70))]),
        "C": T(100, 100, [("w", "in", "W", (30, 40)), ("o", "out", "N", (50, 60))]),
        "Dt": T(100, 100, [("i", "in", "S", (50, 60)), ("w", "in", "W", (60, 70))]),
    }
    parts = [P("a", "A", 0, 0), P("b", "B", 0, 100), P("c", "C", 100, 0, orient_right), P("d", "Dt", 100, 100)]
    if orient_right == "MY":            # mirror c and d: windows measured from the other side
        types["C"] = T(100, 100, [("w", "in", "E", (30, 40)), ("o", "out", "N", (40, 50))])
        types["Dt"] = T(100, 100, [("i", "in", "S", (40, 50)), ("w", "in", "E", (60, 70))])
        parts[3]["orient"] = "MY"
    ports = [port("ab", "a", "o", "b", "i"), port("ac", "a", "e", "c", "w"), port("cd", "c", "o", "d", "i"), port("bd", "b", "e", "d", "w")]
    return plan(types, parts, ports, 200, 200)


def test_row_tie_pads_the_short_neighbour_on_its_type_high_side():
    raw = row_with_tops()
    cand = copy.deepcopy(raw)
    cand["partition_types"]["A"]["outline_um"] = [100, 120]
    Q, rep = D.refloor(raw, cand, log=lambda *a: None)
    parts = {p["name"]: p for p in Q["partitions"]}
    assert parts["b"]["origin_um"][1] == 120 and parts["d"]["origin_um"][1] == 120
    assert rep["padded_types"] == {"C": {"y": 20.0}}
    assert Q["partition_types"]["C"]["outline_um"] == [100, 120.0]
    assert Q["partition_types"]["C"]["buses"] == raw["partition_types"]["C"]["buses"]   # type frame untouched
    assert D.plan_check(Q) == [] and rep["conflicts"] == []


def test_mirrored_growth_keeps_die_windows():
    """an MY partition that grows in x grows on its die-west side; its N window stays put in the die frame."""
    raw = row_with_tops("MY")
    cand = copy.deepcopy(raw)
    cand["partition_types"]["C"]["outline_um"] = [120, 100]
    Q, rep = D.refloor(raw, cand, log=lambda *a: None)
    assert rep["conflicts"] == [] and D.plan_check(Q) == []
    # c widens west of its anchor (east edge); a keeps x, so c / d shift east together; no pad
    parts = {p["name"]: p for p in Q["partitions"]}
    assert parts["c"]["origin_um"][0] == 100 and parts["d"]["origin_um"][0] == 120
    assert Q["die"]["outline_um"][0] == 220


def test_rigid_conflict_is_reported_not_forced():
    """a wide top partition tied by N/S ports to two columns: the left column cannot widen."""
    types = {
        "L": T(100, 100, [("o", "out", "N", (10, 20))]),
        "R": T(100, 100, [("o", "out", "N", (10, 20))]),
        "W": T(200, 100, [("i0", "in", "S", (10, 20)), ("i1", "in", "S", (110, 120))]),
    }
    raw = plan(types, [P("l", "L", 0, 0), P("r", "R", 100, 0), P("w", "W", 0, 100)],
               [port("p0", "l", "o", "w", "i0"), port("p1", "r", "o", "w", "i1")], 200, 200)
    cand = copy.deepcopy(raw)
    cand["partition_types"]["L"]["outline_um"] = [120, 100]
    Q, rep = D.refloor(raw, cand, log=lambda *a: None)
    kinds = {c["kind"] for c in rep["conflicts"]}
    assert "rigid_overlap" in kinds


def test_channel_ports_and_rects_move():
    types = {"lo": T(100, 100, [("o", "out", "N", (10, 20))]), "hi": T(100, 100, [("i", "in", "S", (10, 20))])}
    raw = plan(types, [P("a", "lo", 0, 0), P("b", "hi", 0, 150)], [port("p", "a", "o", "b", "i")], 100, 250,
               channels=[{"between": ["a", "b"], "width_um": 50, "layers": ["M7"], "ports": ["p"]},
                         {"rect_um": [0, 100, 100, 150], "reason": "keep-out"}])
    cand = copy.deepcopy(raw)
    cand["partition_types"]["lo"]["outline_um"] = [100, 110]
    Q, rep = D.refloor(raw, cand, log=lambda *a: None)
    assert {p["name"]: p for p in Q["partitions"]}["b"]["origin_um"] == [0, 160]
    assert Q["die"]["channels"][1]["rect_um"] == [0, 110, 100, 160]
    assert D.plan_check(Q) == [] and rep["conflicts"] == []


def test_reticle_flag():
    raw = column()
    cand = copy.deepcopy(raw)
    cand["partition_types"]["lo"]["outline_um"] = [100, 40000]
    Q, rep = D.refloor(raw, cand, log=lambda *a: None)
    assert rep["reticle_fits"] is False


def test_fit_reticle_reverts_the_biggest_overflow():
    raw = column()
    cand = copy.deepcopy(raw)
    cand["partition_types"]["lo"]["outline_um"] = [100, 33000]
    cand["partition_types"]["hi"]["outline_um"] = [100, 120]
    C, reverted, rep = D.fit_reticle(raw, cand, raw, log=lambda *a: None)
    assert [r["type"] for r in reverted] == ["lo"] and rep["reticle_fits"]
    assert C["partition_types"]["hi"]["outline_um"] == [100, 120]


def test_sidecar_regions_follow_partitions():
    raw = column()
    cand = copy.deepcopy(raw)
    cand["partition_types"]["lo"]["outline_um"] = [100, 130]
    Q, rep = D.refloor(raw, cand, log=lambda *a: None)
    side = {"regions": [{"tag": "r0", "box_um": [0, 0, 120, 110], "parts": ["a"]},
                        {"tag": "r1", "box_um": [0, 110, 120, 220], "parts": ["b"]}]}
    assert D.remap_sidecar(raw, Q, side) == 2
    assert side["regions"][0]["box_um"] == [0, 0, 120, 140] and side["regions"][1]["box_um"] == [0, 140, 120, 250]


def test_io_rect_follows_its_partition():
    raw = column()
    raw["die"]["io"] = [{"name": "io0", "part": "b", "rect_um": [20, 150, 40, 160]}]
    cand = copy.deepcopy(raw)
    cand["partition_types"]["lo"]["outline_um"] = [100, 130]
    Q, rep = D.refloor(raw, cand, log=lambda *a: None)
    assert Q["die"]["io"][0]["rect_um"] == [20, 180, 40, 190]
