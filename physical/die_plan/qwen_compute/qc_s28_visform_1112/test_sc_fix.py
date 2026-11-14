import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sc_fix as F
import visform as V


def block(x, y0, n=40):
    return [[x + 2.16 * (i % 2), round(y0 + 0.27 * (i // 2), 6)] for i in range(n)]


def sc_type(last_x=298.8, last_y=1290.0, win=(1360.0, 1470.0), k=4):
    regs = [[0.0, 1310.0]] + [[115.0 * j, 1310.0] for j in range(1, k - 1)] + [[last_x, last_y]]
    bits = [block(r[0] - 2.9, r[1] - 3.0) for r in regs[1:]]
    return dict(outline_um=[613.44, 1831.68],
                hard_cores=[dict(inst="u_core", origin_um=[302.4, 980.8], outline_um=[244.56, 514.08])],
                ft_slots=[dict(name="x_stm_fe", in_face="W", out_face="E", in_window_um=[1300.0, 1320.0],
                               out_window_um=list(win), stations=k, regs_um=regs, bit_sites_um=bits)])


def run(t):
    plan = dict(partition_types={"sle_sc_v9": t})
    ops, rows = [], []
    F.fix_type("sle_sc_v9", t, ops, rows, plan)
    out, bad = V.apply_ops(plan, dict(ops=ops))
    assert not bad
    return out["partition_types"]["sle_sc_v9"]["ft_slots"][0], rows


def test_flank_station_is_resited_within_target():
    s, rows = run(sc_type())
    assert rows[0]["action"] == "move" and rows[0]["cur_max"] > F.LIMIT
    assert rows[0]["new_max"] <= F.TARGET
    last, prev = s["regs_um"][-1], s["regs_um"][-2]
    a, b = F.legs(prev, last, 613.44, 1415.0)
    assert max(a, b) == rows[0]["new_max"] or abs(max(a, b) - rows[0]["new_max"]) < 0.1


def test_unreachable_window_is_kept_not_half_moved():
    # out window far N of the chain: no legal spot brings both legs under LIMIT -> slot left as is, no ops
    t = sc_type(win=(1700.0, 1800.0))
    s, rows = run(t)
    assert rows[0]["action"] == "keep"
    assert s == sc_type(win=(1700.0, 1800.0))["ft_slots"][0]


def test_moved_block_clear_of_core_and_complete():
    s, rows = run(sc_type())
    core = (302.4 - V.HALO, 980.8 - V.HALO, 547.0 + V.HALO, 1494.9 + V.HALO)
    assert not any(V.inside(p, core, 0.0) for p in s["bit_sites_um"][-1])
    assert len(s["bit_sites_um"][-1]) == 40 and s["regs_um"][:-1] == sc_type()["ft_slots"][0]["regs_um"][:-1]


def test_short_leg_is_left_alone():
    _, rows = run(sc_type(win=(1280.0, 1300.0), last_y=1290.0, last_x=298.8, k=4))
    assert rows == []                          # 314.6 um leg <= LIMIT: not triggered


def test_station_off_the_flank_is_not_touched():
    _, rows = run(sc_type(last_x=250.0))
    assert rows == []
