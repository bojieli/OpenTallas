from types import SimpleNamespace
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import Report, check_clock_branch_buffers


def _t(bxy, legs_ok=True, parent="b0"):
    far = 100.0 if legs_ok else 500.0
    return dict(hard_cores=[dict(inst="tileA", origin_um=[0, 0], outline_um=[50, 50]),
                            dict(inst="tileB", origin_um=[0, 300], outline_um=[50, 50])],
                clock=dict(taps=[dict(name="tileA", xy=[50, 25], parent=parent),
                                 dict(name="tileB", xy=[50, 25 + 2 * far], parent=parent)],
                           branch_buffers=[dict(name="b0", xy=bxy, drives=["tileA", "tileB"])]))


def test_corridor_buffer_ok():
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": _t([60, 125])}), r)
    assert not r.errors() and out["buffers"] == 1 and out["worst_leg_um"] == 110.0


def test_buffer_on_hard_core_fails():
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": _t([25, 25])}), r)
    assert out["types"] == ["root"] and any("inside hard core" in e["msg"] if isinstance(e, dict) else "inside hard core" in str(e) for e in r.errors())


def test_leg_over_reach_fails():
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": _t([50, 525], legs_ok=False)}), r)
    assert out["types"] == ["root"]


def test_parent_must_match():
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": _t([60, 125], parent="nope")}), r)
    assert out["types"] == ["root"] and len(r.errors()) >= 2


def test_buffer_in_station_halo_fails():
    tt = _t([60, 125])
    tt["ft_slots"] = [dict(name="Lx", regs_um=[[61.0, 125.5]], bit_site_cell_um=[1.404, 0.27])]
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": tt}), r)
    assert out["types"] == ["root"]


def test_buffer_clear_of_station_ok():
    tt = _t([60, 125])
    tt["internal_stations"] = [dict(conn="a|b", regs_um=[[70.0, 125.0]])]
    r = Report()
    check_clock_branch_buffers(SimpleNamespace(types={"root": tt}), r)
    assert not r.errors()


def _rep(name, tap, k, xy):
    return dict(name=name, tap=tap, k=k, xy=xy, cell_ll_um=[xy[0] - 0.7, xy[1]], cell_wh_um=[1.404, 0.27])


def test_symmetric_leg_repeaters_ok():
    tt = _t([60, 125])
    tt["clock"]["branch_buffers"][0]["leg_repeaters"] = [_rep("rA", "tileA", 1, [60, 75]),
                                                         _rep("rB", "tileB", 1, [60, 175])]
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": tt}), r)
    assert not r.errors() and out["leg_repeaters"] == 2


def test_asymmetric_leg_repeaters_fail():
    tt = _t([60, 125])
    tt["clock"]["branch_buffers"][0]["leg_repeaters"] = [_rep("rA", "tileA", 1, [60, 75])]
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": tt}), r)
    assert out["types"] == ["root"]


def test_leg_repeater_on_core_fails():
    tt = _t([60, 125])
    tt["clock"]["branch_buffers"][0]["leg_repeaters"] = [_rep("rA", "tileA", 1, [40, 30]),
                                                         _rep("rB", "tileB", 1, [60, 175])]
    r = Report()
    out = check_clock_branch_buffers(SimpleNamespace(types={"root": tt}), r)
    assert out["types"] == ["root"]
