"""ft_channel_route (FT-CHANNEL-ROUTE-1, FABLE-FIX-S81-STRIP 11-17): a bundle is routed through a channel only while the
channel's vertical tracks carry it (each slot charged once), it may cross an M5-ceiling core on the M7 budget but not an
M7 core, and the station chain keeps its count with every hop in reach and at most one stage per channel."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import ft_channel_route as R  # noqa: E402

PER, HPER, LIM = 45.6, 25.8, 0.70


def core(inst, x, y, w, h, obs="M7"):
    return dict(inst=inst, module=inst, origin_um=[x, y], outline_um=[w, h], orient="R0", obs_max=obs)


def slot(name, width, win, sites=None):
    return dict(name=name, width=width, in_face="N", out_face="S", in_window_um=list(win), out_window_um=list(win),
                stations=4, layers=["M7", "M5"], regs_um=[[sum(win) / 2, 800.0]], bit_sites_um=sites or [])


def strip(cores, slots=()):
    return dict(outline_um=[604.8, 800.0], hard_cores=cores, ft_slots=list(slots))


def xs(g, path):
    return [(i + .5) * R.G for i, _ in path]


def test_seam_takes_one_bundle_then_the_next_goes_round():
    # 34.56-um west seam beside an M7 core: 0.70 x 45.6 x 34.56 = 1,103 bits
    t = strip([core("ve", 34.56, 200.0, 172.8, 345.6)])
    g = R.Grid(t, PER, HPER, LIM)
    a, b = R.face_cell(g, "N", (4.0, 30.0)), R.face_cell(g, "S", (4.0, 30.0))
    p1 = g.route("ft0", 669, a, b, 1.0)
    assert p1 and max(xs(g, p1)) < 34.56                       # straight down the seam
    g.charge("ft0", 669, g.path_regs(p1))
    p2 = g.route("ft1", 669, a, b, 1.0)
    assert p2 and max(xs(g, p2)) > 34.56 + 172.8               # 1,338 > 1,103: the second bundle rounds the core
    g.charge("ft0", 669, g.path_regs(p1))                      # charging the same slot again adds nothing
    seam = [r for r in g.chan if g.rect[r][2] <= 34.56 + 1e-6]
    assert seam and all(g.load(r, None) == 669 for r in seam)


def test_no_route_when_every_gap_is_short():
    # full-width M7 wall with one 17.28-um slit: 551 bits fit, 669 do not
    t = strip([core("a", 0.0, 300.0, 293.76, 100.0), core("b", 311.04, 300.0, 293.76, 100.0)])
    g = R.Grid(t, PER, HPER, LIM)
    a, b = R.face_cell(g, "N", (280.0, 320.0)), R.face_cell(g, "S", (280.0, 320.0))
    assert g.route("s", 669, a, b, 1.0) is None
    assert g.route("s", 500, a, b, 1.0) is not None


def test_bundle_crosses_m5_core_on_m7_budget_only():
    wall = lambda obs: strip([core("a", 0.0, 300.0, 604.8, 100.0, obs)])
    a = lambda g: (R.face_cell(g, "N", (280.0, 320.0)), R.face_cell(g, "S", (280.0, 320.0)))
    g7 = R.Grid(wall("M7"), PER, HPER, LIM)
    assert g7.route("s", 100, *a(g7), 1.0) is None            # M7 core over the full width: no way through
    g5 = R.Grid(wall("M5"), PER, HPER, LIM)
    cap = R.OVER_USE * PER * R.M7_SHARE * 604.8                # about 4,027 bits on M7 over the core
    assert g5.route("s", int(cap) - 10, *a(g5), 1.0) is not None
    assert g5.route("s", int(cap) + 10, *a(g5), 1.0) is None


def test_stage_plan_keeps_count_reach_and_one_stage_per_channel():
    t = strip([core("ve", 34.56, 200.0, 172.8, 345.6)])
    g = R.Grid(t, PER, HPER, LIM)
    a, b = R.face_cell(g, "N", (4.0, 30.0)), R.face_cell(g, "S", (4.0, 30.0))
    p = g.route("ft0", 277, a, b, 1.0)
    plan, cost = R.stage_plan(g, p, 4, 12.0, 4.0, 26.0, 394.0, [])
    assert plan is not None and len(plan) == 3 and cost <= 394.0
    ys = [c[1] for c, _ in plan]
    assert ys == sorted(ys, reverse=True)
    assert sum(1 for y in ys if 200.0 - 4 <= y <= 545.6 + 4) <= 1          # one stage at most inside the seam
    hops = [800.0 - ys[0]] + [u - v for u, v in zip(ys, ys[1:])] + [ys[-1]]
    assert max(hops) <= 394.0
    none, why = R.stage_plan(g, p, 2, 12.0, 4.0, 26.0, 394.0, [])            # 800 um in 2 hops: over reach
    assert none is None and "too long" in why


def test_band_stays_out_of_a_channel_the_bundle_does_not_run_through():
    # the bundle runs down x = 250 beside the core's east face; its bands may not stray into the 34.56-um west seam
    t = strip([core("ve", 34.56, 200.0, 172.8, 345.6)])
    g = R.Grid(t, PER, HPER, LIM)
    a, b = R.face_cell(g, "N", (240.0, 262.0)), R.face_cell(g, "S", (240.0, 262.0))
    p = g.route("ft0", 277, a, b, 1.0)
    seam = {r for r in g.chan if g.rect[r][2] <= 34.56 + 1e-6}
    assert not seam & g.path_regs(p)
    plan, _ = R.stage_plan(g, p, 4, 12.0, 4.0, 22.0, 394.0, [g.rect[r] for r in seam])
    assert plan is not None and all(c[0] - e / 2 > 34.56 + 172.8 for c, e in plan if 196.0 <= c[1] <= 549.6)
