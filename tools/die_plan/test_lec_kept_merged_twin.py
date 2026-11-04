"""LEC-KEEP-1 11-03 (class KEEP-MERGED): QC su_lane l6 / S81 ve_s routed LEC proved every compare point, 0 differ,
but KEEP FAIL on kept bits synthesis merged into a surviving twin (ve_s x_sw[i] == ~x_bz[i], xr0c[i] == xr[i]).
A missing kept bit passes only when every miter output is proved and its gold eq chain (each step's hypothesis output
proved) ends in a surviving netlist flop.  Mutants: an unproved / differing step, any unproved miter output, a root
that is not in the netlist, a constant / cube / gate-only form, a cycle.
python3 -m pytest -q tools/die_plan/test_lec_kept_merged_twin.py"""
from types import SimpleNamespace

import lec

K, R, M = "ff:u_dut.t.x_sw[0]", "ff:u_dut.t.x_bz[0]", "ff:u_dut.t.mid[0]"


def _L(hyp, gate=(R,), gold=(K, R, M)):
    return SimpleNamespace(hyp=hyp, tp={g: 1 for g in gate}, gp={g: 1 for g in gold})


def _st(*keys, base=("po:o[0]",)):
    return {n: "proved" for n in list(base) + [f"hyp:gold:{k}" for k in keys]}


def test_merged_twin_proved_equal_to_surviving_flop_passes():
    L = _L({("gold", K): ("eq", "gold", R, 1)})
    assert lec.kept_merged_twins(L, [K], _st(K)) == {K: (R, 1)}


def test_chain_to_surviving_flop_passes_with_polarity():
    L = _L({("gold", K): ("eq", "gold", M, 1), ("gold", M): ("eq", "gold", R, 1)})
    assert lec.kept_merged_twins(L, [K], _st(K, M)) == {K: (R, 0)}


def test_renamed_surviving_flop_passes():
    # the twin survives under a gate-only name proved equal to it
    L = _L({("gold", K): ("eq", "gold", R, 0), ("gate", "ff:u_dut.t.x_bz_reg_0"): ("eq", "gold", R, 0)},
           gate=("ff:u_dut.t.x_bz_reg_0",))
    assert lec.kept_merged_twins(L, [K], _st(K)) == {K: (R, 0)}


def test_non_equal_bit_fails():
    # mutant: the eq step for K is not proved (it differs) -> the whole miter is not all-proved -> stays missing
    L = _L({("gold", K): ("eq", "gold", R, 0)})
    st = _st(); st[f"hyp:gold:{K}"] = "differs"
    assert lec.kept_merged_twins(L, [K], st) == {}
    # mutant: no proof output for the step at all
    assert lec.kept_merged_twins(L, [K], _st()) == {}
    # mutant: a compare point differs / undecided elsewhere
    for bad in ("differs", "undecided"):
        st = _st(K); st["po:o[1]"] = bad
        assert lec.kept_merged_twins(L, [K], st) == {}
    assert lec.kept_merged_twins(L, [K], {}) == {}


def test_no_hypothesis_or_root_not_in_netlist_fails():
    assert lec.kept_merged_twins(_L({}), [K], _st()) == {}
    L = _L({("gold", K): ("eq", "gold", R, 0)}, gate=())
    assert lec.kept_merged_twins(L, [K], _st(K)) == {}
    # root is itself a missing kept bit (the dead-twin class rule owns that case, not this one)
    L = _L({("gold", K): ("eq", "gold", R, 0)})
    assert lec.kept_merged_twins(L, [K, R], _st(K)) == {}


def test_other_forms_and_cycles_fail():
    L = _L({("gold", K): ("const", 0)})
    assert lec.kept_merged_twins(L, [K], _st(K)) == {}
    L = _L({("gold", K): ("cube", "gold", [R, M], [1, 0])})
    assert lec.kept_merged_twins(L, [K], _st(K)) == {}
    L = _L({("gold", K): ("eq", "gate", R, 0)})
    assert lec.kept_merged_twins(L, [K], _st(K)) == {}
    L = _L({("gold", K): ("eq", "gold", M, 0), ("gold", M): ("const", 1)})
    assert lec.kept_merged_twins(L, [K], _st(K, M)) == {}
    L = _L({("gold", K): ("eq", "gold", M, 0), ("gold", M): ("eq", "gold", K, 0)})
    assert lec.kept_merged_twins(L, [K], _st(K, M)) == {}
