"""DIE-S81-92 (FABLE-PD-S81-0335 B(c)): opt-in --depth-guard-ps in count_align_plan, and the die_chain_ca.sh
CA_PLAN_ARGS / CA_BIND_ARGS pass-through + --tools pointing at the dir that holds clk_aocv / die_sta_related."""
import importlib.util
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location("cap_g", Path(__file__).with_name("count_align_plan.py"))
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
T = 833.0
AP = T / 8


def row(port, s, d, dd, up, dn, unsh=0.0):
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=unsh, unshared_b_ps=unsh,
                margin_ps=T / 2 - max(abs(dd + up), abs(dd - dn)))


def rows():
    # a -> b tree edge + a parallel crossing whose window fits DEPTH 4 with less than 1 T to spare
    return [row("ab", "a", "b", 0, 40, 40), row("ab_n", "a", "b", 0, 1.2 * T, 1.2 * T)]


def run(guard, allow=frozenset(), max_depth=8):
    cap.DEPTH_GUARD_PS, cap.DEPTH16_ALLOW = guard, frozenset(allow)
    try:
        s, out, regs = cap.plan(rows(), T, AP, 0.0, max_depth=max_depth)
    finally:
        cap.DEPTH_GUARD_PS, cap.DEPTH16_ALLOW = 0.0, frozenset()
    return s, {o["port"]: o for o in out}


def test_default_guard_zero_is_unchanged():
    s, o = run(0.0)
    assert o["ab_n"]["depth"] == 4 and o["ab"]["depth"] == 4 and s["fail"] == 0
    assert (3.5 * T - AP) - o["ab_n"]["L_hi_ps"] < T                 # within 1 T of the D4 limit


def test_guard_promotes_to_next_depth_and_keeps_k():
    s0, o0 = run(0.0)
    s1, o1 = run(T)
    assert o1["ab_n"]["depth"] == 8 and o1["ab_n"]["rtl"]["DEPTH"] == 8 and o1["ab"]["depth"] == 4
    assert o1["ab_n"]["K"] == o0["ab_n"]["K"] and o1["ab_n"]["lat_cycles"] == o0["ab_n"]["lat_cycles"]
    assert o1["ab_n"]["margin_hi_ps"] >= T and s1["depth8"] == s0["depth8"] + 1


def test_guard_needs_depth16_allow_beyond_depth8():
    # with guard 5 T the row no longer fits D8 either: fails without the D16 opt-in, takes D16 with it
    s, o = run(5 * T)
    assert o["ab_n"]["depth"] is None and s["fail"] == 1
    s, o = run(5 * T, allow={"ab_n"})
    assert o["ab_n"]["depth"] == 16 and s["fail"] == 0


def test_cli_flag_present():
    src = Path(__file__).with_name("count_align_plan.py").read_text()
    assert "--depth-guard-ps" in src and "DEPTH_GUARD_PS = float(a.depth_guard_ps" in src


def test_chain_pass_through_and_tools_dir():
    sh = Path(__file__).with_name("die_chain_ca.sh").read_text()
    assert re.search(r'count_align_plan\.py" "\$OUT/landed_phase_ocv\.json" \$\{CA_PLAN_ARGS:-\}', sh)
    assert re.search(r'count_align_bind\.py" "\$OUT/count_align_plan\.json" \$\{CA_BIND_ARGS:-\}', sh)
    assert '--tools "$T" ' in sh and '--tools "$T/.."' not in sh
