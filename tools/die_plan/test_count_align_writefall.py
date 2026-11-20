"""S81-CLOCK-WINDOW-1119: --write-fall-plan plans K/DEPTH for the fall-write lag L + T/2 that die_sta_related
--ca-write-fall times (S81 cw6: rise-planned K failed 136 crossings on the guard, hi -304 ps)."""
import importlib.util
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cap", HERE / "count_align_plan.py")
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
T = 833.0
AP = T / 8


def row(port, s, d, dd, up, dn):
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=0.0, unshared_b_ps=0.0,
                margin_ps=T / 2 - max(abs(dd + up), abs(dd - dn)))


def _plan(rows, fall):
    cap.WRITE_FALL = frozenset(fall)
    try:
        return cap.plan(rows, T, AP, 0.0)
    finally:
        cap.WRITE_FALL = frozenset()


def gate(o, fall):
    """die_sta_related count-aligned margins on the plan's own L (fall adds T/2 to the lag)."""
    sh = T / 2 if fall else 0.0
    return o["L_lo_ps"] + sh - T / 2, (o["depth"] - 0.5) * T - o["L_hi_ps"] - sh


def test_rise_plan_unchanged_without_flag():
    o = _plan([row("ab", "a", "b", 300, 40, 60)], ())[1][0]
    assert o["K_eff"] == math.ceil((T / 2 + AP - 240) / T) and "write_edge" not in o


def test_fall_port_takes_K_for_lag_plus_half_period():
    rise = _plan([row("ab", "a", "b", 300, 40, 60)], ())[1][0]
    fall = _plan([row("ab", "a", "b", 300, 40, 60)], ("ab",))[1][0]
    assert fall["K_eff"] == math.ceil((T / 2 + AP - T / 2 - 240) / T) == rise["K_eff"] - 1
    assert fall["write_edge"] == "fall" and fall["depth"] == 4
    lo, hi = gate(fall, True)
    assert lo >= AP - 1e-6 and hi >= AP - 1e-6
    assert abs(fall["margin_lo_ps"] - lo) < 0.06 and abs(fall["margin_hi_ps"] - hi) < 0.06


def test_rise_K_timed_as_fall_breaks_the_guard_and_fall_plan_fixes_it():
    # a crossing whose rise-planned window sits high in depth 4: timed fall-write it loses T/2 on the high side
    rows = [row("ab", "a", "b", 900, 60, 60)]
    rise = _plan(rows, ())[1][0]
    assert gate(rise, True)[1] < gate(rise, False)[1] - T / 2 + 1e-6
    fall = _plan([row("ab", "a", "b", 900, 60, 60)], ("ab",))[1][0]
    assert min(gate(fall, True)) >= AP - 1e-6


def test_write_fall_of_uses_the_bind_rule():
    plan = {"clock": {"ring_hold": {"write_edge": "fall", "write_fall_types": ["rx"]}},
            "partitions": [{"name": "p0", "type": "rx"}, {"name": "p1", "type": "tx"}, {"name": "p2", "type": "rx__s1"}],
            "ports": [{"id": "x0", "dst": {"part": "p0"}}, {"id": "x1", "dst": {"part": "p1"}},
                      {"id": "x2", "dst": {"part": "p2"}}]}
    assert cap.write_fall_of(plan, {"x0", "x1", "x2", "x9"}) == {"x0", "x2"}
    plan["clock"]["ring_hold"] = {"write_edge": "rise"}
    assert cap.write_fall_of(plan, {"x0"}) == frozenset()


def test_fall_write_die_plans_zero_guard_fails_under_fall_timing():
    # a small fall-write die (every receiver writes on the fall): each planned crossing, timed the way
    # die_sta_related --ca-write-fall times it, keeps both margins >= ap (0 lag / guard fails)
    import random
    rng = random.Random(6)
    regs = [f"r{i}" for i in range(8)]
    rows = []
    for i in range(1, 8):
        rows.append(row(f"t{i}", regs[rng.randrange(i)], regs[i], rng.uniform(-900, 900), 40, 40))
    for j in range(24):
        a, b = rng.sample(regs, 2)
        rows.append(row(f"x{j}", a, b, rng.uniform(-1500, 1500), rng.uniform(100, 600), rng.uniform(100, 600)))
    ports = {r["port"] for r in rows}
    s, out, _ = _plan([dict(r) for r in rows], ports)
    planned = [o for o in out if o.get("depth")]
    assert len(planned) >= 20
    for o in planned:
        if o["kind"] == "tree_ambiguous":
            continue
        lo, hi = gate(o, True)
        assert lo >= AP - 0.06 and hi >= AP - 0.06, o
    rise = {o["port"]: o for o in _plan([dict(r) for r in rows], ())[1] if o.get("depth")}
    assert any(min(gate(o, True)) < AP - 0.06 for o in rise.values())    # the rise plan would fail fall timing
