import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fp_floorplan as A  # noqa: E402
import ft_core_detour as D  # noqa: E402


def _plan(flag=True):
    # one 240x240 core in a 1200x700 type; a 2-station chain whose middle hop runs straight through it
    ty = dict(outline_um=[1200.0, 700.0],
              hard_cores=[dict(inst="c0", origin_um=[480.0, 200.0], outline_um=[240.0, 240.0])],
              buses=[dict(name="b", width=64)],
              internal_stations=[dict(conn="bus:b", launch="bus b", from_um=[380.0, 500.0], to_um=[820.0, 140.0],
                                      regs_um=[[460.0, 340.0], [740.0, 300.0]])],
              ft_slots=[])
    raw = dict(partition_types={"t": ty})
    if flag:
        raw["ft_core_detour"] = {"enable": 1}
    return raw


def _nonl(ty):
    bx = D._boxes(ty)
    return sum(w for w, pts, nm in A._lanes(ty) for a, b in zip(pts, pts[1:])
               if any(A._inside_um(a, b, x) >= A.CROSS_MIN_UM for x in bx) and not D.clear_manhattan(a, b, bx))


def test_flag_absent_byte_identical(tmp_path):
    raw = _plan(flag=False)
    src = tmp_path / "p.json"
    src.write_text(json.dumps(raw))
    out = tmp_path / "o.json"
    sys.argv = ["x", str(src), "--out", str(out)]
    assert D.main() == 0
    assert out.read_bytes() == src.read_bytes()
    r, led = D.apply(raw)
    assert r is raw and led == [] and json.dumps(raw) == src.read_text()


def test_resite_clears_crossing_keeps_station_count_and_reach():
    raw = _plan()
    ty = raw["partition_types"]["t"]
    n0 = len(ty["internal_stations"][0]["regs_um"])
    assert _nonl(ty) > 0
    raw, led = D.apply(raw)
    ty = raw["partition_types"]["t"]
    s = ty["internal_stations"][0]
    assert len(s["regs_um"]) == n0                      # no added cycle
    assert _nonl(ty) == 0
    pts = [s["from_um"]] + s["regs_um"] + [s["to_um"]]
    assert all(D._man(a, b) <= D.REACH_BUDGET + 1e-6 for a, b in zip(pts, pts[1:]))
    assert s["from_um"] == [380.0, 500.0] and s["to_um"] == [820.0, 140.0]     # fixed ends untouched
    assert any(x.get("kind") == "station_chain" and x["bad_hops_after"] < x["bad_hops_before"] for x in led)


def test_unfixable_chain_left_unchanged():
    raw = _plan()
    s = raw["partition_types"]["t"]["internal_stations"][0]
    s["regs_um"] = []                                    # single 700-um hop: no station to move, must stay as planned
    before = json.dumps(raw["partition_types"])
    raw, led = D.apply(raw)
    assert json.dumps(raw["partition_types"]) == before


def test_manhattan_mode_and_default_unchanged():
    ty = _plan()["partition_types"]["t"]
    strict = A.core_crossings(ty)
    assert strict and A.core_crossings(ty, manhattan=False) == strict
    assert A.core_crossings(ty, manhattan=True) == strict          # a hop straight through the core stays a crossing
    # corner-clipping diagonal: crossing in the straight model only, an L (via x 470 / y 190) clears the core
    ty["internal_stations"][0].update(from_um=[470.0, 450.0], regs_um=[], to_um=[730.0, 190.0])
    assert A.core_crossings(ty) and A.core_crossings(ty, manhattan=True) == []


def test_ft_slot_interior_station_moves_with_its_bit_sites_ends_stay():
    raw = _plan()
    ty = raw["partition_types"]["t"]
    ty["internal_stations"] = []
    ty["outline_um"] = [900.0, 700.0]
    old = [[330.0, 500.0], [460.0, 340.0], [740.0, 300.0], [860.0, 140.0]]
    ty["ft_slots"] = [dict(name="ft0", in_face="W", width=1, stations=5,
                           regs_um=[[0.0, 500.0]] + [list(p) for p in old],
                           bit_sites_um=[[[p[0], p[1]], [p[0], p[1] + 0.27]] for p in old])]
    assert _nonl(ty) > 0
    raw, led = D.apply(raw)
    s = raw["partition_types"]["t"]["ft_slots"][0]
    assert len(s["regs_um"]) == 5 and len(s["bit_sites_um"]) == 4          # station count unchanged
    assert s["regs_um"][1] == old[0] and s["regs_um"][4] == old[3]          # first and last station pinned
    assert any(x.get("kind") == "ft_slot" and x["bad_hops_after"] < x["bad_hops_before"] for x in led)
    for k, (ox, oy) in enumerate(old):
        dx, dy = s["regs_um"][k + 1][0] - ox, s["regs_um"][k + 1][1] - oy
        assert abs(s["bit_sites_um"][k][0][0] - (ox + dx)) < 1e-3 and abs(s["bit_sites_um"][k][1][1] - (oy + 0.27 + dy)) < 1e-3
    assert _nonl(raw["partition_types"]["t"]) == 0


def test_station_never_lands_on_another_station_cell():
    raw = _plan()
    ty = raw["partition_types"]["t"]
    # a second chain already holds the best detour corner; the re-sited station must not share its 12-um cell
    ty["internal_stations"].append(dict(conn="bus:b", launch="bus b", from_um=[380.0, 500.0], to_um=[380.0, 520.0],
                                        regs_um=[[477.5, 442.5]]))
    raw, _ = D.apply(raw)
    s = raw["partition_types"]["t"]["internal_stations"][0]
    ctx = D.Ctx(raw["partition_types"]["t"])
    cells = [ctx._ck(q) for q in s["regs_um"]] + [ctx._ck([477.5, 442.5])]
    assert len(cells) == len(set(cells))


def test_schema_registers_flag():
    import copy
    import schema
    import test_schema
    p = schema.SCHEMA["properties"]["ft_core_detour"]
    assert p["additionalProperties"] is False and set(p["properties"]) == {"enable", "types"}
    base = copy.deepcopy(test_schema.EX)
    assert schema.validate({**base, "ft_core_detour": {"enable": 1}}) == []
    assert schema.validate({**base, "ft_core_detour": {"enable": 1, "bogus": 1}})
