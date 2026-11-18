"""KV-D24-HUBC 11-18: clksite_resite moves a die clock tree site that a hard core covers by the smallest legal
axis move (here S, clear of core + halo), keeps uncovered sites and other kinds, and fails closed past --max-move-um.
    python3 -m pytest -q tools/die_plan/test_clksite_resite.py"""
import copy

import clksite_resite as R


def _plan():
    t = dict(outline_um=[400.0, 400.0],
             hard_cores=[dict(inst="pv", module="m", origin_um=[100.0, 100.0], outline_um=[200.0, 190.0], orient="R0")],
             clock=dict(reserved_sites_um=[
                 dict(rect_um=[200.0, 150.0, 202.16, 151.35], kind="die_clock_tree", route_layers="M1-M7"),
                 dict(rect_um=[350.0, 150.0, 352.16, 151.35], kind="die_clock_tree", route_layers="M1-M7"),
                 dict(rect_um=[150.0, 290.5, 152.16, 291.85], kind="die_clock_tree", route_layers="M1-M7"),   # near, not under
                 dict(rect_um=[200.0, 120.0, 210.0, 130.0], kind="landing_ring_bank")]))
    return dict(partition_types=dict(T=t), partitions={"p": dict(type="T", origin_um=[1000.0, 2000.0])})


def test_covered_site_moves_smallest_legal_axis_move():
    p = _plan()
    led = R.run(p, halo=2.16)
    assert len(led) == 1 and led[0]["index"] == 0 and led[0]["dir"] == "S"
    new = led[0]["new"]
    assert new[3] <= 100.0 - 2.16 and abs((new[3] - new[1]) - 1.35) < 1e-6 and new[0] == 200.0
    assert abs(led[0]["move_um"] - (151.35 - new[3])) < 1e-6
    rs = p["partition_types"]["T"]["clock"]["reserved_sites_um"]
    assert rs[0]["rect_um"] == new and rs[1]["rect_um"] == [350.0, 150.0, 352.16, 151.35]   # uncovered site kept
    assert rs[2]["rect_um"] == [150.0, 290.5, 152.16, 291.85]                               # inside halo only: kept
    assert led[0]["die_centre_um"]["p"] == [1201.08, round(2000.0 + (new[1] + new[3]) / 2, 4)]


def test_blocked_direction_steps_on_and_max_move_fails_closed():
    p = _plan()
    # a register point right under the S landing pushes the S candidate one more row down
    p["partition_types"]["T"]["internal_stations"] = [dict(regs_um=[[201.0, 97.0]])]
    led = R.run(copy.deepcopy(p), halo=2.16)
    assert led[0]["dir"] == "S" and led[0]["new"][3] < 97.0 - 0.5
    led = R.run(copy.deepcopy(p), halo=2.16, max_move=5.0)
    assert led[0]["new"] is None
