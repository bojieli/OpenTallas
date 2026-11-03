"""DIE-QC-64/SUL 11-02: QC su_lane l1 routed LEC proved 86101/86101 compare points but KEEP FAIL 96 bits
(u_u_lrly1.idr[503..598]): ORFS eliminate_dead_logic removed kept flops the synthesized netlist reads nowhere, while
the gold AIG still reaches them structurally.  A missing kept bit is exempt only when EVERY compare point was proved
with it an unpaired free input (no accepted correspondence hypothesis names it); a merge (eq hypothesis on it, or a
gate flop paired with it) or any unproved point keeps it fail-closed (mutants).
python3 -m pytest -q tools/die_plan/test_lec_kept_functional_unobservable.py"""
from types import SimpleNamespace

import lec


def _L(hyp):
    return SimpleNamespace(hyp=hyp)


def test_free_unpaired_kept_bit_with_all_points_proved_is_exempt():
    L = _L({("both", "ff:u_dut.z"): ("const", 0), ("gold", "ff:u_dut.a"): ("eq", "gold", "ff:u_dut.b", 0)})
    assert lec.kept_functionally_unobservable(L, ["ff:u_dut.idr[503]", "ff:u_dut.idr[504]"], True) == \
        ["ff:u_dut.idr[503]", "ff:u_dut.idr[504]"]


def test_merged_kept_bit_stays_missing():
    # mutant: the kept bit was merged into its twin (accepted eq hypothesis on it) -> not exempt
    L = _L({("gold", "ff:u_dut.idr[503]"): ("eq", "gold", "ff:u_dut.c_dsi[0]", 0)})
    assert lec.kept_functionally_unobservable(L, ["ff:u_dut.idr[503]"], True) == []


def test_kept_bit_named_as_merge_target_stays_missing():
    # mutant: another register (gate or gold) was proved equal to the kept bit -> it carries state, not exempt
    L = _L({("gate", "ff:u_dut.clone"): ("eq", "gold", "ff:u_dut.idr[503]", 1)})
    assert lec.kept_functionally_unobservable(L, ["ff:u_dut.idr[503]"], True) == []
    L = _L({("gate", "ff:u_dut.cube"): ("cube", "gold", ["ff:u_dut.idr[503]", "ff:u_dut.x"], [0, 1])})
    assert lec.kept_functionally_unobservable(L, ["ff:u_dut.idr[503]"], True) == []


def test_constant_kept_bit_not_reclassified_here():
    L = _L({("both", "ff:u_dut.idr[503]"): ("const", 0)})
    assert lec.kept_functionally_unobservable(L, ["ff:u_dut.idr[503]"], True) == []


def test_any_unproved_compare_point_exempts_nothing():
    # mutant: a compare point differs / is undecided -> the free bit may be what it reads: fail closed
    assert lec.kept_functionally_unobservable(_L({}), ["ff:u_dut.idr[503]"], False) == []
    assert lec.kept_functionally_unobservable(_L({}), [], True) == []
