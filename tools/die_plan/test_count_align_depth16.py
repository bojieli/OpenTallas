"""DIE-S81-11 (METHODOLOGY 12.16 b(iii), COORD 07:20 (2)): opt-in DEPTH 16 in count_align_plan (--max-depth 16)."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("cap", Path(__file__).with_name("count_align_plan.py"))
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
T = 833.0
AP = T / 8


def row(port, s, d, dd, up, dn, unsh=1000.0):
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=unsh, unshared_b_ps=unsh,
                margin_ps=T / 2 - max(abs(dd + up), abs(dd - dn)))


def wide():
    # a -> b tree edge; parallel a -> b crossing whose derated interval is 9 periods wide: > D8 window, < D16 window
    return [row("ab", "a", "b", 0, 40, 40, unsh=0.0), row("ab_w", "a", "b", 0, 4.5 * T, 4.5 * T, unsh=0.0)]


def test_default_is_depth8_and_wide_crossing_fails():
    s, out, regs = cap.plan(wide(), T, AP, 0.0)
    o = {x["port"]: x for x in out}
    assert s["max_depth"] == 8 and s["depth16"] == 0
    assert o["ab_w"]["depth"] is None and s["fail"] == 1          # unchanged without the opt-in


def test_depth16_opt_in_takes_wide_crossing_with_ap_margins_and_mc():
    rows = wide()
    s, out, regs = cap.plan(rows, T, AP, 0.0, max_depth=16)
    o = {x["port"]: x for x in out}
    w = o["ab_w"]
    assert s["fail"] == 0 and s["depth16"] == 1 and w["depth"] == 16 and w["rtl"]["DEPTH"] == 16
    assert w["rtl"]["GUARD_HI"] == 16 and o["ab"]["depth"] == 4          # narrow crossings keep the smallest depth
    assert w["margin_lo_ps"] >= AP - 1e-6 and w["margin_hi_ps"] >= AP - 1e-6
    assert abs(w["margin_hi_ps"] - (15.5 * T - w["L_hi_ps"])) < 0.06
    for r in rows:
        r["lo"], r["hi"] = r["d_ps"] - r["p_dn_ps"], r["d_ps"] + r["p_up_ps"]
    assert cap.mc_check(rows, out, regs, T, 600)[1] == 0
    w["depth"] = 8                                                          # mutant: D8 ring for the same K -> violates
    assert cap.mc_check(rows, out, regs, T, 600)[1] > 0


def test_depth16_not_used_when_depth8_fits():
    rows = [row("ab", "a", "b", 0, 40, 40, unsh=0.0), row("ab2", "a", "b", 0, 2 * T, 2 * T, unsh=0.0)]
    s8, out8, _ = cap.plan([dict(r) for r in rows], T, AP, 0.0)
    s16, out16, _ = cap.plan([dict(r) for r in rows], T, AP, 0.0, max_depth=16)
    assert [o["depth"] for o in out8] == [o["depth"] for o in out16] and s16["depth16"] == 0
    assert [o["K"] for o in out8] == [o["K"] for o in out16]


def test_bad_max_depth_refused():
    with pytest.raises(ValueError):
        cap.plan(wide(), T, AP, 0.0, max_depth=32)
